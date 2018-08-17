sites = {
    'null': {},
}

sites['personal-site'] = {
    'path': './personal_site',
    'templates': ['index.html', 'gallery-card.html', 'gallery-thumbnail.html', 'sidebar.html'],
    'params': {
        'baseurl': 'http://localhost/'
    }
}

# global params for all of sites
# Note: please use https://www.srihash.org/ to hash third-party js/css library
params = {
    'jquery_js_tag': '<script src="https://code.jquery.com/jquery-3.3.1.min.js" integrity="sha256-FgpCb/KJQlLNfOu91ta32o/NMZxltwRo8QtmkMRdAu8=" crossorigin="anonymous"></script>',
    'popper_js_tag': '<script src="https://cdnjs.cloudflare.com/ajax/libs/popper.js/1.14.0/umd/popper.min.js" integrity="sha384-cs/chFZiN24E4KMATLdqdvsezGxaGsi4hLGOzlXwp5UZB1LY//20VyM2taTB4QvJ" crossorigin="anonymous"></script>',
    'bootstrap_css_tag': '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.0/css/bootstrap.min.css" integrity="sha384-9gVQ4dYFwwWSjIDZnLEWnxCjeSWFphJiwGPXr1jddIhOegiu1FwO5qRGvFXOdJZ4" crossorigin="anonymous">',
    'bootstrap_js_tag': '<script src="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/4.1.0/js/bootstrap.min.js" integrity="sha384-uefMccjFJAIv6A+rW+L4AHf99KvxDjWSu1z9VI8SKNVmz4sk7buKt/6v9KI65qnm" crossorigin="anonymous"></script>',
    'holder_js_tag': '<script src="https://cdnjs.cloudflare.com/ajax/libs/holder/2.9.4/holder.min.js" integrity="sha384-MpKPJqgKw6H2j/qCkQtzi0Vd0Z+3y6KzXp14HmTpXRQH//zby2a3MEuCpj7KJf2n" crossorigin="anonymous"></script>',
    'clipboard_js_tag': '<script src="https://cdnjs.cloudflare.com/ajax/libs/clipboard.js/2.0.0/clipboard.min.js" integrity="sha384-5tfO0soa+FisnuBhaHP2VmPXQG/JZ8dLcRL43IkJFzbsXTXT6zIX8q8sIT0VSe2G" crossorigin="anonymous"></script>',
}


site_static_dirname = 'static'
site_partials_dirname = 'partials'
site_output_dirname = 'output'
site_tpl_encoding = 'utf8'
site_cfg_filename = 'config.json'

server_port = 80