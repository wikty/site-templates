import re
import sys
import copy
import time
import shutil
import hashlib
import os
import json
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

def remove_html_comment_filter(content):
    return re.sub(r'<!--(.*?)-->', '', content)

def render_tpl(site, env, tpl, site_cfg, site_params, output_dir, ignore_html_comment=False, output_encoding='utf8'):
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
    if ignore_html_comment:
        c = remove_html_comment_filter(c)
    output_file = os.path.join(output_dir, tpl)
    dirname = os.path.dirname(output_file)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(output_file, 'w', encoding=output_encoding) as f:
        f.write(c)
    return os.path.normcase(output_file), c

def render_site(site, 
                cfg_filename, 
                output_dirname,
                static_dirname, 
                msg_file, 
                cmd_params={}, 
                tpl_encoding='utf8', 
                ignore_html_comment=False):
    if (os.path.normcase(os.path.normpath(output_dirname)).lower() == 
            os.path.normcase(os.path.normpath(static_dirname)).lower()):
        raise Error('Site static directory cannot be same with output directory')
    # re-create output directory and copy static resources
    site_dir = config.sites[site]['path']
    templates = config.sites[site]['templates']
    static_dir = os.path.join(site_dir, static_dirname)
    output_dir = os.path.join(site_dir, output_dirname)
    cfg_file = os.path.join(site_dir, cfg_filename)        
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    if not os.path.isdir(static_dir):
        os.makedirs(output_dir)
    else:
        shutil.copytree(static_dir, output_dir)
    # init
    site_cfg = load_site_config(cfg_file)
    site_params = load_site_params(site, site_cfg, cmd_params)
    env = Environment(loader=FileSystemLoader(site_dir, tpl_encoding))
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
                                        ignore_html_comment)
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
                                                ignore_html_comment)
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

def watcher(src_dir, dest_dir, renderer, render_kwargs, exclude_regex, msg_file, interval=1):
    oldhash = hashsite(src_dir, exclude_regex)
    while True:
        time.sleep(interval)
        newhash = hashsite(src_dir, exclude_regex)
        if oldhash != newhash:
            oldhash = newhash
            message('Watcher',
                    'Site changed, start re-render it')
            renderer(**render_kwargs)
            message('Watcher',
                    'Site render is done!')

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
    # Handler = http.server.SimpleHTTPRequestHandler
    # httpd = socketserver.TCPServer(("", port), Handler)
    # message('Server',
    #         'start server',
    #         msg_file,
    #         **{'listening on port': port})
    # httpd.serve_forever()
    httpd = HTTPServer(current_dir, root_dir, ("", port))
    message('Server',
            'start server',
            msg_file,
            **{'listening on port': port})
    httpd.serve_forever()

def server_site(site, port, watch, server, watcher, renderer, render_kwargs):
    site_dir = config.sites[site]['path']
    msg_file = render_kwargs['msg_file']
    output_dirname = render_kwargs['output_dirname']
    output_dir = os.path.join(site_dir, output_dirname)
    current_dir = os.getcwd()
    try:
        server_thread = threading.Thread(name="server",
                                         target=server, 
                                         args=(current_dir, 
                                               output_dir, 
                                               port, 
                                               msg_file))
        server_thread.start()
        if watch:
            regex = re.compile(r'(\.md$|{})'.format(output_dirname))
            watch_thread = threading.Thread(name="watcher",
                                            target=watcher,
                                            args=(site_dir, 
                                                  output_dir, 
                                                  renderer, 
                                                  render_kwargs,
                                                  regex,
                                                  msg_file))
            watch_thread.start()
    except KeyboardInterrupt:
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
    parser.add_argument("-e", "--encoding", 
                        help="Site template encoding. Default: %(default)s", 
                        default=config.site_tpl_encoding)
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
                        help="Ignore template html comment", 
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


    render_kwargs = {
        'site': site,
        'cfg_filename': args.cfg,
        'output_dirname': args.output,
        'static_dirname': args.static,
        'msg_file': args.messageio,
        'cmd_params': params,
        'tpl_encoding': args.encoding,
        'ignore_html_comment': args.ignore
    }
    render_site(**render_kwargs)

    if args.server:
        server_site(site, 
                    args.port,
                    args.watch,
                    server,
                    watcher,
                    render_site,
                    render_kwargs)