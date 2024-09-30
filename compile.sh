python -m PyInstaller buzz.py -F --paths "venv/Lib/site-packages" --add-data "buzzmain/templates;templates" --add-data "buzzmain/static;static" --icon=buzzmain/static/favicon.ico --clean
read -p "Press [Enter]"
mv dist/buzz.exe buzz.exe
rm -rfd dist
rm -rfd __pycache__
rm -rfd buzzmain/__pycache__
rm -rfd build
rm -rfd buzz.egg-info
rm *.spec
read -p "Press [Enter]"