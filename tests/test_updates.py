from litewin import updates


def test_makescript_updates():
    script = updates.makescript()
    assert "wuauserv" in script
    assert "WaaSMedicSvc" in script
    assert "UsoSvc" in script
    assert "dosvc" in script
    assert "NoAutoUpdate" in script
    assert "AUOptions" in script
    assert "SetDisableUXWUAccess" in script
    assert "Disable-ScheduledTask" in script
