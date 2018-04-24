## Introduction

Some sites are made by template engine [Jinja2](http://docs.jinkan.org/docs/jinja2/index.html).

## Usage

### Site Templates

See more about [Jinja2](http://docs.jinkan.org/docs/jinja2/templates.html) template syntax.

Site structrue example:

[Personal Site](./personal_site) is built based on [Twitter Bootstrap](http://getbootstrap.com/) framework.

```
personal_site
    - static # static resources directory
    - partials # sub-templates directory
    - base.html # base template
    - index.html # template
    - gallery.html # template
    - config.json # site configuration file
```

Please go to `config.py` and set `sites['site-id']['templates']` list to specify which templates'll be rendered.

### Site Context/Parameters

* For all of sites

    Fill the `params` variable in the `config.py`.

* For a site

    There are three ways to specify template parameters:

    * Fill the `sites['site-id']['params']` variable in the `config.py`
    * Add configuration into site `config.json`'s `global` dictionary.
    * Provide by command line's `--params` option, e.g., `a=1;b=2` 

* For one template of a site

    Add configuration into site `config.json`'s `local` dictionary, using template path as key.

### Site Static

All of files and directories in the site's `static` will be copied into the generated site top-level directory.




