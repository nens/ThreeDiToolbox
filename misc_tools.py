# (c) Nelen & Schuurmans, see LICENSE.rst.
"""
Miscellaneous tools.
"""
from ThreeDiToolbox.utils.user_messages import pop_up_info


class About(object):

    def __init__(self, iface):
        self.iface = iface
        self.icon_path = ":/plugins/ThreeDiToolbox/icons/icon_sunset.png"
        self.menu_text = "3Di about"

    def run(self):
        pop_up_info(
            """Thank you for installing the sunset version of 3Di Toolbox.

3Di Toolbox has been replaced by the 3Di Schematisation Editor (for viewing and editing schematisations) and 3Di Result Analysis (for analysing simulation results). Please install these two plugins through the Plugin Manager.

You may still need to load layers from the 3Di spatialite to fix errors reported by the schematisation checker. For this purpose, the 3Di Toolbox sunset version still allows you to add the spatialite layers to your project. This is a temporary situation, while the 3Di team is preparing the phasing out of the spatialite and transitioning to geopackage entirely.""",
            "About", self.iface.mainWindow())

    def on_unload(self):
        pass
