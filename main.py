import re
import sys
import copy
import shutil
import os
import json
import argparse
import http.server
import socketserver

from jinja2 import Environment, FileSystemLoader
from jinja2.exceptions import TemplateNotFound, TemplateSyntaxError

import config

__version__ = "1.0.0"

def cmd_parse_params(args):
    '''
    args example: language="zh-cn";count=19
    '''
    regex = re.compile(r'(?P<key>[-_a-zA-Z0-9]+)=(?P<quote>[\'"]?)(?P<value>.+?)(?P=quote)(;|$)')
    params = {}
    for m in regex.finditer(args):
        params[m.group('key')] = m.group('value')
    return params

def cmd_parse_site(site):
    if site in config.sites:
        return site.strip('"').strip("'")

def message(service, msg='', **kwargs):
    print('[{}] {}'.format(service, msg))
    print('\t{}'.format(', '.join(['{}: {}'.format(k, v) for k,v in kwargs.items()])))

def load_site_config(site, encoding='utf8'):
    file = os.path.join(config.sites[site]['path'], config.site_cfg_filename)
    cfg = {}
    with open(file, 'r', encoding=encoding) as f:
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

def render_tpl(site, env, tpl, site_cfg, site_params, output_dir, output_encoding='utf8'):
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
    output_file = os.path.join(output_dir, tpl)
    dirname = os.path.dirname(output_file)
    if not os.path.isdir(dirname):
        os.makedirs(dirname)
    with open(output_file, 'w', encoding=output_encoding) as f:
        f.write(c)
    return os.path.normcase(output_file), c

def render_site(site, output_dir, cmd_params={}, tpl_encoding='utf8'):
    # re-create output directory and copy static resources
    site_dir = config.sites[site]['path']
    site_static_dir = os.path.join(site_dir, config.site_static_dir)
    if os.path.isdir(output_dir):
        shutil.rmtree(output_dir)
    if not os.path.isdir(site_static_dir):
        os.makedirs(output_dir)
    else:
        shutil.copytree(site_static_dir, output_dir)
    # init
    site_cfg = load_site_config(site)
    site_params = load_site_params(site, site_cfg, cmd_params)
    env = Environment(loader=FileSystemLoader(site_dir, tpl_encoding))
    # render templates
    for path in config.sites[site]['templates']:
        full_path = os.path.join(site_dir, path)
        if os.path.isfile(full_path):
            output, content = render_tpl(site, env, path, site_cfg, site_params, output_dir)
            message('Render', 
                    'ouput file', 
                    **{'template': output, 'size': len(content)})
        elif os.path.isdir(full_path):
            for current_dir, dirs, files in os.walk(full_path):
                for file in files:
                    if not file.endswith('.html'):
                        continue
                    tpl = os.path.relpath(os.path.join(current_dir, file), site_dir)
                    output, content = render_tpl(site, env, tpl, site_cfg, site_params, output_dir)
                    message('Render', 
                            'ouput file', 
                            **{'template': output, 'size': len(content)})
        else:
            message('Render', 
                    'invalid template', 
                    **{'template': path})

def server_site(site, root_dir, port=80):
    current_dir = os.getcwd()
    try:
        os.chdir(root_dir)
        Handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", port), Handler)
        message('Server',
                'start server',
                **{'listening on port': port})
        httpd.serve_forever()
    except KeyboardInterrupt:
        os.chdir(current_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Generate Bootstrap example site, template powered by Jinja2.")
    parser.add_argument("site",
                        help="The site name you want to be generated", default="")
    parser.add_argument("-p", "--params",
                        help="Pass parameter variables into template parser, e.g., a=1;b=2", default="")
    parser.add_argument("-s", "--server", 
                        help="Run server", action="store_true")
    parser.add_argument("-v", "--verbose", 
                        help="Output verbosity", action="store_true")
    parser.add_argument("-V", "--version", 
                        help="Show version", action="store_true")
    args = parser.parse_args()
    
    if args.version:
        print(sys.argv[0], __version__)
        sys.exit()

    params = cmd_parse_params(args.params)
    site = cmd_parse_site(args.site)
    
    if not site:
        print('The site {} not in examples.'.format(args.site))
        sys.exit()

    render_site(site, config.site_output_dir, params, 'utf8')

    if args.server:
        server_site(site, config.site_output_dir)