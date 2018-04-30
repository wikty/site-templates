import re
import sys
import copy
import time
import shutil
import hashlib
import os
import json
import signal
import argparse
import threading
import http.server
import socketserver
from http.server import HTTPServer as BaseHTTPServer, SimpleHTTPRequestHandler


from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

import config

__version__ = "1.0.0"

class Error(Exception):
    pass

def cmd_parse_params(args, jsonfile):
    '''
    args example: language="zh-cn";count=19
    jsonfile: a json file contains key-value parameters
    '''
    params = {}
    if jsonfile:
        with jsonfile:
            params = json.load(jsonfile)
    regex = re.compile(r'^(?P<key>[-_a-zA-Z0-9]+)=(?P<quote>[\'"]?)(?P<value>.+?)(?P=quote)$')
    for item in args:
        m = regex.match(item)
        if not m:
            raise Error('command line params parsing error: %s' % item)
        params[m.group('key')] = m.group('value')
    return params

def cmd_parse_site(site):
    if site in config.sites:
        return site.strip('"').strip("'")

def message(service, msg='', file=sys.stdout, **kwargs):
    print('[{}] {}'.format(service, msg), file=file)
    if kwargs:
        print('\t{}'.format(', '.join(['{}: {}'.format(k, v) for k,v in kwargs.items()])), file=file)

def load_site_config(cfg_file, encoding='utf8'):
    cfg = {}
    with open(cfg_file, 'r', encoding=encoding) as f:
        cfg = json.load(f)
    return cfg

def load_site_params(site, site_cfg={}, cmd_params={}):
    p = {}
    # params for all of sites
    p.update(config.params)
    # params for the specifically site via config.py
    p.update(config.sites[site].get('params', {}))
    # params for the specifically site via site's config.json
    p.update(site_cfg.get('global', {}))
    # params for the specifically site via command-line
    p.update(cmd_params)
    return p

def load_tpl_params(site, tpl, site_cfg={}, site_params={}):
    p = copy.deepcopy(site_params)
    # params for the specifically template in the site via config.json
    tpl_keys = []
    s = tpl[:]
    while s:
        tpl_keys.append(s)
        s = os.path.dirname(s)
    for tpl_key in tpl_keys[::-1]:
        p.update(site_cfg.get('local', {}).get(tpl_key, {}))
    # template inner parameters
    baseurl = site_params.get('baseurl', site_cfg.get('global', {}).get('baseurl', '/'))
    url = '/{}'.format(tpl.strip('/'))
    p.update({
        'SITE': site,
        'BASE_URL': baseurl,
        'URL': url,
        'ABS_URL': '/'.join([baseurl.rstrip('/'), url.lstrip('/')]),
    })
    return p

# template filters
def remove_html_comment_filter(tpl, content):
    return re.sub(r'<!--(.*?)-->', '', content, flags=re.DOTALL)

def remove_empty_line_filter(tpl, content):
    return re.sub(r'^\s*$', '', content, flags=re.MULTILINE)

# load render parameters/configuration
def render_init(site, 
                cfg_filename, 
                output_dirname,
                static_dirname, 
                partials_dirname,
                cmd_params={},
                tpl_encoding='utf8'):
    norm_output_dirname = os.path.normcase(os.path.normpath(output_dirname)).lower()
    if ((norm_output_dirname == 
            os.path.normcase(os.path.normpath(static_dirname)).lower()) or (
        norm_output_dirname ==
            os.path.normcase(os.path.normpath(partials_dirname)).lower())):
        raise Error('Site output directory cannot be same with static and partials directory')
    # re-create output directory and copy static resources
    site_dir = config.sites[site]['path']
    templates = config.sites[site]['templates']
    static_dir = os.path.join(site_dir, static_dirname)
    partials_dir = os.path.join(site_dir, partials_dirname)
    output_dir = os.path.join(site_dir, output_dirname)
    cfg_file = os.path.join(site_dir, cfg_filename)     
    site_cfg = load_site_config(cfg_file)
    site_params = load_site_params(site, site_cfg, cmd_params)
    env = Environment(loader=FileSystemLoader(site_dir, tpl_encoding))
    return {
        'site_dir': site_dir,
        'static_dir': static_dir,
        'partials_dir': partials_dir,
        'output_dir': output_dir,
        'site_cfg': site_cfg,
        'site_params': site_params,
        'env': env,
        'templates': templates
    }

# render a template
def render_tpl(site, env, tpl, site_cfg, site_params, output_dir, filters=[], output_encoding='utf8'):
    '''
    tpl: directory separator is /, not \
    '''
    tpl = tpl.replace('\\', '/')
    params = load_tpl_params(site, tpl, site_cfg, site_params)
    try:
        t = env.get_template(tpl)
        c = t.render(**params)
    except TemplateNotFound as e:
        raise
    except TemplateSyntaxError as e:
        raise
    for f in filters:
        c = f(tpl, c)
    output_file = os.path.join(output_dir, tpl)
    dirname = os.path.dirname(output_file)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(output_file, 'w', encoding=output_encoding) as f:
        f.write(c)
    return os.path.normcase(output_file), c

# render a site
def render_site(site, 
                cfg_filename, 
                output_dirname,
                static_dirname, 
                partials_dirname,
                msg_file, 
                cmd_params={}, 
                tpl_encoding='utf8', 
                filters=[]):
    data = render_init(site,
                    cfg_filename,
                    output_dirname,
                    static_dirname,
                    partials_dirname,
                    cmd_params,
                    tpl_encoding)
    site_dir = data['site_dir']
    output_dir = data['output_dir']
    static_dir = data['static_dir']
    partials_dir = data['partials_dir']
    site_cfg = data['site_cfg']
    site_params = data['site_params']
    env = data['env']
    templates = data['templates']
    # clean output dir and copy static dir
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    if not os.path.isdir(static_dir):
        os.makedirs(output_dir)
    else:
        shutil.copytree(static_dir, output_dir)
    # render templates
    for path in templates:
        full_path = os.path.join(site_dir, path)
        if os.path.isfile(full_path):
            output, content = render_tpl(site, 
                                        env, 
                                        path, 
                                        site_cfg, 
                                        site_params, 
                                        output_dir,
                                        filters)
            message('Render', 
                    'ouput file', 
                    msg_file,
                    **{'template': output, 'size': len(content)})
        elif os.path.isdir(full_path):
            for current_dir, dirs, files in os.walk(full_path):
                for file in files:
                    if not file.endswith('.html'):
                        continue
                    tpl = os.path.relpath(os.path.join(current_dir, file), site_dir)
                    output, content = render_tpl(site, 
                                                env, 
                                                tpl, 
                                                site_cfg, 
                                                site_params, 
                                                output_dir,
                                                filters)
                    message('Render', 
                            'ouput file', 
                            msg_file,
                            **{'template': output, 'size': len(content)})
        else:
            message('Render', 
                    'invalid template', 
                    msg_file,
                    **{'template': path})

def hashsite(site_dir, exclude_regex=r''):
    '''
    site_dir: site root directory
    exclude_regex: regex for exclude dirs&files
    '''
    def hashdir(dirpath, hash):
        for entry in os.scandir(dirpath):
            if exclude_regex.match(os.path.relpath(entry.path, site_dir)):
                continue
            if entry.is_file():
                mtime = os.path.getmtime(entry.path)
                hash.update(str(mtime).encode())
                hash.update(entry.name.encode())
            if entry.is_dir():
                hashdir(entry.path, hash)
        return hash

    return hashdir(site_dir, hashlib.sha256()).digest()

class WatchThread(threading.Thread):

    def __init__(self, *args, **kwargs):
        '''
        args, kwargs: for thread's worker/target function
        '''
        super().__init__()
        self.args = args
        self.kwargs = kwargs
        # watch interval seconds
        self.interval = 1
        # stop flag event
        self.stop_event = threading.Event()

    def stop(self):
        self.stop_event.set()

    def worker(self, src_dir, dest_dir, renderer, render_kwargs, exclude_regex, msg_file):
        oldhash = hashsite(src_dir, exclude_regex)
        while True:
            if self.stop_event.is_set():
                break
            time.sleep(self.interval)
            newhash = hashsite(src_dir, exclude_regex)
            if oldhash != newhash:
                oldhash = newhash
                message('Watcher', 'Site changed, start re-render it')
                renderer(**render_kwargs)
                message('Watcher', 'Site render is done!')
        message('Watcher', 'Bye! Bye!')

    def run(self):
        self.worker(*self.args, **self.kwargs)

class HTTPHandler(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        path = SimpleHTTPRequestHandler.translate_path(self, path)
        relpath = os.path.relpath(path, self.server.cwd)
        fullpath = os.path.join(self.server.root_dir, relpath)
        return fullpath

class HTTPServer(BaseHTTPServer):
    def __init__(self, cwd, root_dir, server_address, RequestHandlerClass=HTTPHandler):
        '''
        cwd: python current working directory
        root_dir: server document root directory
        '''
        BaseHTTPServer.__init__(self, server_address, RequestHandlerClass)
        self.cwd = cwd
        self.root_dir = root_dir

def server(current_dir, root_dir, port, msg_file):
    # start server in current working directory
    # Handler = http.server.SimpleHTTPRequestHandler
    # httpd = socketserver.TCPServer(("", port), Handler)
    # message('Server',
    #         'start server',
    #         msg_file,
    #         **{'listening on port': port})
    # httpd.serve_forever()

    # start server in root_dir directory
    httpd = HTTPServer(current_dir, root_dir, ("", port))
    message('Server',
            'start server',
            msg_file,
            **{'listening on port': port})
    httpd.serve_forever()

def server_site(site, port, watching, renderer, render_kwargs):
    site_dir = config.sites[site]['path']
    msg_file = render_kwargs['msg_file']
    output_dirname = render_kwargs['output_dirname']
    output_dir = os.path.join(site_dir, output_dirname)
    current_dir = os.getcwd()
    # start watch thread(optional)
    watch_thread = None
    if watching:
        regex = re.compile(r'(\.md$|{})'.format(output_dirname))
        watch_thread = WatchThread(site_dir, 
                                  output_dir, 
                                  renderer, 
                                  render_kwargs,
                                  regex,
                                  msg_file)
        watch_thread.start()
    # start server in main thread, so that KeyboardInterrupt can be captured
    try:
        server(current_dir, output_dir, port, msg_file)
    except KeyboardInterrupt:
        # elegant termination watcher thread
        if watch_thread is not None:
            watch_thread.stop()
            watch_thread.join()
        message('Server',
            'Bye, Bye!',
            msg_file)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Generate Bootstrap example site, templates are powered by Jinja2.",
        epilog="Happy! Bang! Boom! Poop!"
    )
    parser.add_argument("site",
                        help="The site id you want to be generated",
                        metavar="SiteID")
    parser.add_argument("-p", "--params",
                        help="Pass parameter variables into template parser, e.g., a=1", 
                        action="append",
                        default=[])
    parser.add_argument("-j", "--json",
                        help="Pass parameter variables via json file(a dict) into template parser", 
                        type=argparse.FileType('r', encoding='utf8'),
                        default=None)
    parser.add_argument("-g", "--config", 
                        help="Site config filename(In Site Dir). Default: %(default)s", 
                        dest="cfg",
                        default=config.site_cfg_filename)
    parser.add_argument("-o", "--output", 
                        help="Output directory name(In Site Dir). Default: %(default)s", 
                        default=config.site_output_dirname)
    parser.add_argument("-s", "--static", 
                        help="Site static directory Name(In Site Dir). Default: %(default)s", 
                        default=config.site_static_dirname)
    parser.add_argument("-t", "--partials", 
                        help="Site template partials directory Name(In Site Dir). Default: %(default)s", 
                        default=config.site_partials_dirname)
    parser.add_argument("-e", "--encoding", 
                        help="Site template encoding. Default: %(default)s", 
                        default=config.site_tpl_encoding)
    parser.add_argument("-T", "--tpl", 
                        help="Render a template", 
                        default="")
    parser.add_argument("-S", "--server", 
                        help="Run server", 
                        action="store_true",
                        default=False)
    parser.add_argument("-P", "--port", 
                        help="Server Port. Default: %(default)s", 
                        dest="port",
                        type=int,
                        nargs="?",
                        const=config.server_port,
                        default=config.server_port)
    parser.add_argument("-W", "--watch", 
                        help="Watch Site Source changing", 
                        action="store_true",
                        default=False)
    parser.add_argument("-i", "--ignore", 
                        help="Ignore template html comment/empty line", 
                        action="store_false")
    parser.add_argument("-m", "--messageio", 
                        help="Write feedback message into the IO object. Type: %(type)s", 
                        nargs="?",
                        metavar="IO",
                        type=argparse.FileType('w'),
                        const=sys.stdout,
                        default=sys.stdout)
    parser.add_argument("-v", "--verbose", 
                        help="Output different verbosity levels by verbose count", 
                        action="count")
    parser.add_argument("-V", "--version", 
                        help="Show version information", 
                        action="version",
                        version=__version__)
    args = parser.parse_args()

    site = cmd_parse_site(args.site)
    params = cmd_parse_params(args.params, args.json)
    
    if not site:
        print('The site {} not in examples.'.format(args.site))
        sys.exit()

    filters = []
    if args.ignore:
        filters.append(remove_html_comment_filter)
        filters.append(remove_empty_line_filter)
        

    if not args.tpl:
        # render the whole site
        render_kwargs = {
            'site': site,
            'cfg_filename': args.cfg,
            'output_dirname': args.output,
            'static_dirname': args.static,
            'partials_dirname': args.partials,
            'msg_file': args.messageio,
            'cmd_params': params,
            'tpl_encoding': args.encoding,
            'filters': filters
        }
        render_site(**render_kwargs)
        # serve the site
        if args.server:
            server_site(site, 
                        args.port,
                        args.watch,
                        render_site,
                        render_kwargs)
    else:
        # render a template, and output in stdout
        pass