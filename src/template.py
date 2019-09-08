"""
This module makes available the template and links needed to generate hypothes.is posts by traxiv.
"""

from string import Template

banners = {}
banners['Molecular Systems Biology'] = "https://www.embopress.org/pb-assets/embo-site/images/RevCo_Transparency-MSB.jpg"
banners['The EMBO Journal']          = "https://www.embopress.org/pb-assets/embo-site/images/RevCo_Transparency-EMBOJ.jpg"
banners['EMBO reports']              = "https://www.embopress.org/pb-assets/embo-site/images/RevCo_Transparency-EMBOR.jpg"
banners['EMBO Molecular Medicine']   = "https://www.embopress.org/pb-assets/embo-site/images/RevCo_Transparency-EMM.jpg"
banners['Life Science Alliance']     = "https://www.embopress.org/pb-assets/embo-site/images/RevCo_Transparency-LSA.jpg"

with open('./templates/embo_press.md') as f:
    template_string = f.read()
    embo_press_template = Template(template_string)
