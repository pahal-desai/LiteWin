import os
import tempfile

from litewin import theme


def test_find_wallpaper():
    wp = theme.findwallpaper()
    assert wp is not None
    assert os.path.isfile(wp)
    assert wp.endswith(".png")


def test_makescript_theme():
    script = theme.makescript(wallpaper_dest="C:\\Windows\\Web\\Wallpaper\\LiteWin\\wallpaper.png", dark=True)
    assert "AppsUseLightTheme" in script
    assert "SystemUsesLightTheme" in script
    assert "SystemParametersInfo" in script
    assert "C:\\Windows\\Web\\Wallpaper\\LiteWin\\wallpaper.png" in script


def test_bundle_theme():
    with tempfile.TemporaryDirectory() as tmp:
        res = theme.bundle(oem_root=tmp, dark=True)
        assert res["wallpaper source"] is not None
        assert res["wallpaper bundled"] is not None
        assert os.path.isfile(res["wallpaper bundled"])
        assert os.path.isfile(res["script"])
        with open(res["script"], "r", encoding="utf-8") as f:
            content = f.read()
            assert "SystemParametersInfo" in content
            assert "AppsUseLightTheme" in content
