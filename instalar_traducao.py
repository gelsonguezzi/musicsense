import argostranslate.package as pkg
try:
    pkg.update_package_index()
    matches=[p for p in pkg.get_available_packages() if p.from_code=='en' and p.to_code=='pt']
    if not matches: print('Pacote en-pt indisponivel. A transcricao funcionara sem traducao.');quit()
    pkg.install_from_path(matches[0].download())
    print('Traducao ingles-portugues instalada.')
except Exception as exc:print('Nao foi possivel instalar traducao:',exc)