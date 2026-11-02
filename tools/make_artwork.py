# -*- coding: utf-8 -*-
"""
PyFreeRdpApp artwork: the application icon and the README / social banner.
The icon is a monitor whose screen shows another window - a desktop within a desktop - with a
yellow pointer reaching into it. The banner repeats that nesting, receding to the right.
Everything is written as SVG (text converted to outlines, so it looks the same on every machine)
and rendered with Qt to PNG, ICO (Windows) and ICNS (macOS).
    python tools/make_artwork.py
Writes PyFreeRdpApp/rdpwidget/images/ (shipped with the package) and assets/ (the banner).
"""
from ManyQt.QtGui import QFont, QGuiApplication, QImage, QPainter, QPainterPath
from ManyQt.QtCore import QByteArray, QRectF, Qt
from ManyQt.QtSvg import QSvgRenderer
from os.path import abspath, dirname, join, exists
from os import makedirs
from sys import argv

ROOT = dirname(dirname(abspath(__file__)))  # type: str
IMAGES = join(ROOT, u'PyFreeRdpApp', u'rdpwidget', u'images')  # type: str
ASSETS = join(ROOT, u'assets')  # type: str
# Palette.
HARBOR = u'#0E2A47'  # type: str
DEEP = u'#0A1F36'  # type: str
SIGNAL = u'#2F6FDE'  # type: str
PHOSPHOR = u'#5CE1E6'  # type: str
SUN = u'#FFD43B'  # type: str
PAPER = u'#F3F6FA'  # type: str
SLATE = u'#8DA2B8'  # type: str
ICON_SIZES = (16, 24, 32, 48, 64, 128, 256, 512)  # type: tuple
SMALL_UP_TO = 32  # type: int  # Sizes up to this use the simplified drawing.


def pointer(x, y, scale, outline):
    """
    The pointer: an arrow with its tip at (x, y).
    :param x: (float) Tip x.
    :param y: (float) Tip y.
    :param scale: (float) 1.0 = 118 units tall.
    :param outline: (float) Outline width.
    :return: (str | unicode) An SVG path element.
    """
    points = ((0, 0), (0, 118), (30, 90), (52, 138), (74, 128), (52, 81), (94, 77))
    d = u' '.join(u'{}{:.1f} {:.1f}'.format(u'M' if i == 0 else u'L', x + px * scale, y + py * scale)
                  for i, (px, py) in enumerate(points)) + u' Z'
    return (u'<path d="{}" fill="{}" stroke="{}" stroke-width="{}" stroke-linejoin="round"/>'
            .format(d, SUN, HARBOR, outline))


def iconSvg(small=False):
    """
    :param small: (bool) The drawing for 16-32 px: no inner window, heavier shapes, and every edge on a
        32-unit grid - whole pixels at 16 and 32 px, so the small icons stay crisp.
    :return: (str | unicode) The icon, 512 x 512.
    """
    if small:
        tile, monitor, screen = (0, 0, 512, 512, 96), (64, 96, 384, 256, 32), (96, 128, 320, 192, 8)
        neck, base, tip, scale, outline, inner = (224, 352, 64, 32), (160, 384, 192, 32, 16), (256, 160), 1.75, 14, u''
    else:
        tile, monitor, screen = (16, 16, 480, 480, 108), (68, 100, 376, 260, 34), (90, 122, 332, 216, 16)
        neck, base, tip, scale, outline = (222, 358, 68, 44), (160, 396, 192, 30, 15), (286, 214), 1.25, 9
        inner = (u'<rect x="146" y="162" width="220" height="136" rx="10" fill="#12365C" stroke="{p}" '
                 u'stroke-width="12"/><rect x="146" y="162" width="220" height="30" rx="10" fill="{p}"/>'
                 u'<rect x="146" y="180" width="220" height="12" fill="{p}"/>'
                 u'<circle cx="168" cy="177" r="6" fill="{h}"/><circle cx="188" cy="177" r="6" fill="{h}"/>'
                 ).format(p=PHOSPHOR, h=HARBOR)
    return u'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512" width="512" height="512">
 <defs>
  <linearGradient id="tile" x1="0" y1="0" x2="1" y2="1">
   <stop offset="0" stop-color="{signal}"/><stop offset="1" stop-color="{harbor}"/>
  </linearGradient>
  <linearGradient id="screen" x1="0" y1="0" x2="0" y2="1">
   <stop offset="0" stop-color="#16406B"/><stop offset="1" stop-color="{deep}"/>
  </linearGradient>
 </defs>
 <rect x="{t[0]}" y="{t[1]}" width="{t[2]}" height="{t[3]}" rx="{t[4]}" fill="url(#tile)"/>
 <rect x="{m[0]}" y="{m[1]}" width="{m[2]}" height="{m[3]}" rx="{m[4]}" fill="{paper}"/>
 <rect x="{s[0]}" y="{s[1]}" width="{s[2]}" height="{s[3]}" rx="{s[4]}" fill="url(#screen)"/>
 {inner}
 <rect x="{n[0]}" y="{n[1]}" width="{n[2]}" height="{n[3]}" fill="{paper}"/>
 <rect x="{b[0]}" y="{b[1]}" width="{b[2]}" height="{b[3]}" rx="{b[4]}" fill="{paper}"/>
 {pointer}
</svg>
'''.format(signal=SIGNAL, harbor=HARBOR, deep=DEEP, paper=PAPER, inner=inner, t=tile, m=monitor, s=screen,
           n=neck, b=base, pointer=pointer(tip[0], tip[1], scale, outline))


def makeFont(family, pixelSize, weight, spacing=0.0):
    """
    :param family: (str | unicode) Font family.
    :param pixelSize: (int) Font size in px.
    :param weight: (int) QFont weight.
    :param spacing: (float) Extra letter spacing, px.
    :return: QFont
    """
    font = QFont(family)  # type: QFont
    font.setPixelSize(pixelSize)
    font.setWeight(weight)
    font.setLetterSpacing(QFont.AbsoluteSpacing, spacing)
    return font


def textPath(text, family, pixelSize, weight, x, y, fill, spacing=0.0):
    """
    Text as an SVG path (outlines), so it does not depend on installed fonts.
    :param text: str | unicode
    :param family: (str | unicode) Font family.
    :param pixelSize: (int) Font size in px.
    :param weight: (int) QFont weight.
    :param x: (float) Left of the baseline.
    :param y: (float) Baseline.
    :param fill: (str | unicode) Color.
    :param spacing: (float) Extra letter spacing, px.
    :return: (str | unicode) An SVG path element.
    """
    font = makeFont(family, pixelSize, weight, spacing)  # type: QFont
    path = QPainterPath()  # type: QPainterPath
    path.addText(x, y, font, text)
    parts, i = [], 0
    while i < path.elementCount():
        e = path.elementAt(i)
        if e.type == QPainterPath.MoveToElement:
            parts.append(u'M{:.2f} {:.2f}'.format(e.x, e.y))
        elif e.type == QPainterPath.LineToElement:
            parts.append(u'L{:.2f} {:.2f}'.format(e.x, e.y))
        elif e.type == QPainterPath.CurveToElement:
            c1, c2 = path.elementAt(i + 1), path.elementAt(i + 2)
            parts.append(u'C{:.2f} {:.2f} {:.2f} {:.2f} {:.2f} {:.2f}'.format(e.x, e.y, c1.x, c1.y, c2.x, c2.y))
            i += 2
        i += 1
    return u'<path d="{}" fill="{}"/>'.format(u' '.join(parts), fill)


def titleWidth(text, family, pixelSize, weight, spacing=0.0):
    """
    The drawn width of a text, as textPath draws it.
    :param text: str | unicode
    :param family: (str | unicode) Font family.
    :param pixelSize: (int) Font size in px.
    :param weight: (int) QFont weight.
    :param spacing: (float) Extra letter spacing, px.
    :return: (float) Width in px.
    """
    font = makeFont(family, pixelSize, weight, spacing)  # type: QFont
    path = QPainterPath()  # type: QPainterPath
    path.addText(0, 0, font, text)
    return path.boundingRect().right()


def bannerSvg():
    """
    :return: (str | unicode) The banner, 1280 x 640 (GitHub's social preview size).
    """
    # The motif: screens within screens, receding into the right edge - in their own zone, clear of the text.
    titleRight = 400 + titleWidth(u'PyFreeRdpApp', u'DejaVu Sans Mono', 88, QFont.Bold, -1.0)  # type: float
    start = titleRight + 64  # type: float  # A clear gap between the text column and the motif.
    frames = []
    for k in range(6):
        w, h = (1280 + 60 - start) - 40 * k, 224 - 31 * k
        x, y = start + 40 * k, 320 - h / 2.0
        frames.append(u'<rect x="{:.1f}" y="{:.1f}" width="{:.1f}" height="{:.1f}" rx="{:.1f}" fill="none" '
                      u'stroke="{}" stroke-opacity="{:.2f}" stroke-width="3"/>'.format(
            x, y, w, h, 22 - 2.5 * k, PHOSPHOR, 0.42 - 0.065 * k))
    title = textPath(u'PyFreeRdpApp', u'DejaVu Sans Mono', 88, QFont.Bold, 400, 300, PAPER, -1.0)
    line1 = textPath(u'Remote desktop for Python.', u'DejaVu Sans', 31, QFont.Normal, 402, 364, SLATE)
    line2 = textPath(u'FreeRDP 3 underneath, Qt on top.', u'DejaVu Sans', 31, QFont.Normal, 402, 406, SLATE)
    install = textPath(u'pip install PyFreeRdpApp', u'DejaVu Sans Mono', 26, QFont.Normal, 402, 474, PHOSPHOR)
    icon = iconSvg().split(u'\n', 1)[1].rsplit(u'</svg>', 1)[0]  # The icon's body, reused as is.
    return u'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1280 640" width="1280" height="640">
 <defs>
  <linearGradient id="sky" x1="0" y1="0" x2="1" y2="1">
   <stop offset="0" stop-color="{harbor}"/><stop offset="1" stop-color="{deep}"/>
  </linearGradient>
  <radialGradient id="glow" cx="0.18" cy="0.5" r="0.45">
   <stop offset="0" stop-color="{signal}" stop-opacity="0.35"/><stop offset="1" stop-color="{signal}" stop-opacity="0"/>
  </radialGradient>
 </defs>
 <rect width="1280" height="640" fill="url(#sky)"/>
 <rect width="1280" height="640" fill="url(#glow)"/>
 {frames}
 <g transform="translate(92 190) scale(0.5)">{icon}</g>
 {title}
 {line1}
 {line2}
 {install}
</svg>
'''.format(harbor=HARBOR, deep=DEEP, signal=SIGNAL, frames=u'\n '.join(frames), icon=icon, title=title, line1=line1,
           line2=line2, install=install)


def render(svg, width, height):
    """
    :param svg: (str | unicode) SVG markup.
    :param width: int
    :param height: int
    :return: QImage
    """
    renderer = QSvgRenderer(QByteArray(svg.encode(u'utf-8')))  # type: QSvgRenderer
    image = QImage(width, height, QImage.Format_ARGB32)  # type: QImage
    image.fill(Qt.transparent)
    painter = QPainter(image)  # type: QPainter
    painter.setRenderHint(QPainter.Antialiasing, True)
    painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
    renderer.render(painter, QRectF(0, 0, width, height))
    painter.end()
    return image


def main():
    """
    :return: (int) 0
    """
    app = QGuiApplication(argv)  # type: QGuiApplication  # Fonts need an application.
    if not exists(IMAGES):
        makedirs(IMAGES)
    if not exists(ASSETS):
        makedirs(ASSETS)
    full, small = iconSvg(), iconSvg(small=True)
    for name, svg in ((u'pyfreerdpapp.svg', full), (u'pyfreerdpapp-small.svg', small)):
        with open(join(IMAGES, name), u'w', newline=u'\n') as fh:
            fh.write(svg)
    pngs = []
    for size in ICON_SIZES:
        path = join(IMAGES, u'pyfreerdpapp-{}.png'.format(size))  # type: str
        render(small if size <= SMALL_UP_TO else full, size, size).save(path)
        pngs.append(path)
    from PIL import Image
    biggest = Image.open(join(IMAGES, u'pyfreerdpapp-256.png'))
    biggest.save(join(IMAGES, u'pyfreerdpapp.ico'), sizes=[(s, s) for s in ICON_SIZES if s <= 256],
                 append_images=[Image.open(p) for p in pngs if int(p.rsplit(u'-', 1)[1][:-4]) <= 256])
    Image.open(join(IMAGES, u'pyfreerdpapp-512.png')).save(join(IMAGES, u'pyfreerdpapp.icns'))
    banner = bannerSvg()  # type: str
    with open(join(ASSETS, u'banner.svg'), u'w', newline=u'\n') as fh:
        fh.write(banner)
    render(banner, 1280, 640).save(join(ASSETS, u'banner.png'))
    render(banner, 2560, 1280).save(join(ASSETS, u'banner@2x.png'))
    print(u'icon: {} sizes + svg/ico/icns in {}'.format(len(ICON_SIZES), IMAGES))
    print(u'banner: svg + png (1x, 2x) in {}'.format(ASSETS))
    del app
    return 0


if __name__ == u'__main__':
    raise SystemExit(main())
