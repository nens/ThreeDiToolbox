from threedi_results_analysis.threedi_plugin import About

import mock


def test_smoke():
    """Test whether ThreeDiAnimation can be instantiated.

    TODO: this was the setUp() of an otherwise empty unittest class.  It
    doesn't look like it actually tests something. Especially the
    toolbar_animation is a mock, so calling that has no use.

    """
    iface = mock.Mock()
    tdi_root_tool = About(iface)
    toolbar_animation = iface.addToolBar("ThreeDiAnimation")
    toolbar_animation.setObjectName("ThreeDiAnimation")
    assert tdi_root_tool
