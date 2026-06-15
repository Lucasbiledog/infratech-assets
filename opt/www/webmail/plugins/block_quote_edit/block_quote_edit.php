
<?php

class block_quote_edit extends rcube_plugin

{

    public $task = 'mail';

    public $allowed_prefs = array();



    public function init()

    {

        $this->add_hook('compose_editor_init', array($this, 'inject_script'));

        $this->add_hook('render_page', array($this, 'inject_script'));

    }



    public function inject_script($args)

    {

        $template = isset($args['template']) ? $args['template'] : '';

        $rcube = rcube::get_instance();

        $script = "

            (function() {

                var bqe_timer = setInterval(function() {

                    if (typeof tinymce === 'undefined') return;

                    var ed = tinymce.get('composebody');

                    if (ed === null || ed === undefined) return;

                    if (ed._bqe_bound) return;

                    ed._bqe_bound = true;

                    clearInterval(bqe_timer);

                    ed.on('keydown', function(e) {

                        var node = ed.selection.getNode();

                        var el = node;

                        while (el && el !== ed.getBody()) {

                            if (el.nodeName === 'BLOCKQUOTE') {

                                e.preventDefault();

                                e.stopImmediatePropagation();

                                return false;

                            }

                            el = el.parentNode;

                        }

                    }, true);

                    ed.on('paste', function(e) {

                        var node = ed.selection.getNode();

                        var el = node;

                        while (el && el !== ed.getBody()) {

                            if (el.nodeName === 'BLOCKQUOTE') {

                                e.preventDefault();

                                return false;

                            }

                            el = el.parentNode;

                        }

                    }, true);

                }, 300);

            })();

        ";

        $rcube->output->add_script($script, 'foot');

        return $args;

    }

}

