import os
import os
import sys

from flask import Flask, request, redirect, render_template, url_for, send_from_directory
from flask_dropzone import Dropzone
from werkzeug.utils import secure_filename

from buzzmain.Marc.marc_tools import *

if getattr(sys, 'frozen', False):
    print('Template folder: ' + str(os.path.join(sys._MEIPASS, 'templates')))
    print('Static folder: ' + str(os.path.join(sys._MEIPASS, 'static')))
    app = Flask(__name__, template_folder=os.path.join(sys._MEIPASS, 'templates'), static_folder=os.path.join(sys._MEIPASS, 'static'))
else:
    app = Flask(__name__)

for suffix in ['uploads', 'output']:
    if not os.path.isdir(os.path.join(os.getcwd(), suffix)):
      os.makedirs(os.path.join(os.getcwd(), suffix))

app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'uploads')
app.config['OUTPUT_FOLDER'] = os.path.join(os.getcwd(), 'output')
app.config['DROPZONE_MAX_FILE_SIZE'] = 1024
app.config['DROPZONE_TIMEOUT'] = 5*60*1000
app.config['DROPZONE_ALLOWED_FILE_CUSTOM'] = True
app.config['DROPZONE_ALLOWED_FILE_TYPE'] = '.MRC, .mrc, .lex'
app.config['DROPZONE_REDIRECT_VIEW'] = 'read_marc'
app.config['DROPZONE_DEFAULT_MESSAGE'] = ('<button class="btn btn-outline-secondary" value="Upload">'
                                          'Drag and drop a file here<br/>or click to upload'
                                          '<i class="px-2 bi bi-file-earmark-arrow-up"></i></button>'
                                          '<br/> <br/>'
                                          '<p><small>Supported files:</small></p>'
                                          '<ul class="list-unstyled">'
                                          '<li><p><small>.MRC (from your Aleph local drive)</small></p></li>'
                                          '<li><p><small>.mrc</small></p></li>'
                                          '<li><p><small>.lex</p></li></ul>')
ALLOWED_EXTENSIONS = {'lex', 'mrc', 'MRC'}
app.secret_key = 'secret dino key'
dropzone = Dropzone(app)


class BuzzValues:

    def __init__(self):
        self.num_input_records = 0
        self.num_z_records = 0
        self.pos_input_records = 0
        self.filename = None
        self.filetype = 'lex'
        self.input_records = {1: None}
        self.z_records = {1: None}
        self.query = None
        self.title = None
        self.au = None
        self.isbn = None
        self.writer = MARCWriter
        self.reader = MARCReader
        self.blid = None


BZ = BuzzValues()


def allowed_file(fname):
    """Function to check whether a filename is valid"""
    return '.' in fname and fname.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/favicon.ico')
def favicon():
    if getattr(sys, 'frozen', False):
        print(os.path.join(sys._MEIPASS, 'static'))
        return send_from_directory(os.path.join(sys._MEIPASS, 'static'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@app.route('/', methods=['GET', 'POST'])
@app.route('/index')
@app.route('/home')
@app.route('/upload', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        if 'file' not in request.files:
            return render_template('index.html')
        file = request.files.get('file')
        if file.filename == '':
            return render_template('index.html')
        if file and allowed_file(file.filename):
            BZ.filename = secure_filename(file.filename)
            if file.filename.rsplit('.', 1)[1] == 'MRC':
                BZ.filetype = 'MRC'
            else:
                BZ.filetype = 'lex'
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], BZ.filename))
            return redirect(url_for('read_marc'))
    return render_template('index.html')


@app.route('/help', methods=['GET', 'POST'])
def buzz_help():
    return render_template('help.html')


@app.route('/uploads/<name>', methods=['GET', 'POST'])
def download_file(name):
    return send_from_directory(app.config['UPLOAD_FOLDER'], name)


@app.route('/read_marc', methods=['GET', 'POST'])
def read_marc():
    if not BZ.filename:
        return redirect(url_for('read_marc'))
    ifile = open(os.path.join(app.config['UPLOAD_FOLDER'], BZ.filename), encoding='utf-8', mode='r', errors='replace')
    r = ifile.read()
    if BZ.filetype == 'MRC':
        BZ.input_records[0] = Record().from_MRC_string(r)
        BZ.num_input_records = 1
    else:
        with open(os.path.join(app.config['UPLOAD_FOLDER'], BZ.filename), mode='rb') as f:
            BZ.num_input_records = f.read().count(29)
        BZ.reader = MARCReader(open(os.path.join(app.config['UPLOAD_FOLDER'], BZ.filename), mode='rb'))
        BZ.input_records[0] = BZ.reader.__next__()
    BZ.writer = MARCWriter(open(os.path.join(app.config['OUTPUT_FOLDER'], BZ.filename), mode='wb'))
    BZ.pos_input_records = 1
    return render_template('process.html', filename=BZ.filename, num_input_records=BZ.num_input_records,
                           pos_input_records=1, record=BZ.input_records[0])


@app.route('/record_number', methods=['GET'])
def record_number():
    return str(BZ.pos_input_records)


@app.route('/next_record', methods=['GET', 'POST'])
def next_record():
    if request.method == 'POST':
        if BZ.pos_input_records < BZ.num_input_records:
            BZ.pos_input_records += 1
            BZ.input_records[BZ.pos_input_records] = BZ.reader.__next__()
            return render_template('marc.html',
                                   filename=BZ.filename,
                                   num_input_records=BZ.num_input_records,
                                   pos_input_records=BZ.pos_input_records,
                                   record=BZ.input_records[BZ.pos_input_records])
        return render_template('finished.html', filename=BZ.filename)


@app.route('/download', methods=['GET', 'POST'])
def download():
    BZ.writer.flush()
    print(app.config['OUTPUT_FOLDER'] + BZ.filename)
    return send_from_directory(directory=app.config['OUTPUT_FOLDER'], path=BZ.filename, mimetype='application/octet-stream', as_attachment=True)


@app.route('/validate', methods=['GET', 'POST'])
def validate():
    if request.method == 'POST':
        r = Record()
        r.from_string(request.form.get('editable_marc'))
        BZ.input_records[BZ.pos_input_records] = r
        valid, errors = r.validate()
        return render_template('validation.html', valid=valid, errors=errors, pos_input_records=BZ.pos_input_records, num_input_records=BZ.num_input_records)
    return render_template('validation.html', pos_input_records=BZ.pos_input_records, num_input_records=BZ.num_input_records)


@app.route('/next_record_with_errors', methods=['GET', 'POST'])
def next_record_with_errors():
    if request.method == 'POST':
        while BZ.pos_input_records < BZ.num_input_records:
            BZ.pos_input_records += 1
            BZ.input_records[BZ.pos_input_records] = BZ.reader.__next__()
            valid, errors = BZ.input_records[BZ.pos_input_records].validate()
            if not valid:
                return render_template('marc.html',
                                       filename=BZ.filename,
                                       num_input_records=BZ.num_input_records,
                                       pos_input_records=BZ.pos_input_records,
                                       record=BZ.input_records[BZ.pos_input_records])
        return render_template('finished.html', filename=BZ.filename)


if __name__ == "__main__":
    app.run(port=4204, debug=True)
