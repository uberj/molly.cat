from hooks import compile_sass

from gallery import Gallery

gallery = Gallery()

hooks = {
    'page.meta.post': [gallery.get_images],
    'page.template.pre': [gallery.get_albums, gallery.set_images],
    'site.output.post': [compile_sass],
}
