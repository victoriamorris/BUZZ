function setupToggle() {
    const formSelectFormat = document.querySelector("#selectFormat");
    formSelectFormat.addEventListener(
        "change",
        (event) => {
            const dataRadioFormat = new FormData(formSelectFormat);
            var radioFormat = dataRadioFormat.get("radioFormat");
            if ( radioFormat == "Aleph" ) {
                var str=$('#editable_marc').val();
                var n=str.replace(/\$/g,'$$$$');
                $('#editable_marc').html(n);
                $('#editable_marc').val(n);
            }
            if ( radioFormat == "Breaker" ) {
                var str=$('#editable_marc').val();
                var n=str.replace(/\$\$/g,'$').replace(/\$\$/g,'$');
                $('#editable_marc').html(n);
                $('#editable_marc').val(n);
            }
            setupHighlighter();
        },
        false,
    );
}


/* Functions for checking records */

function setupHighlighter(){
    const formSelectFormat = document.querySelector("#selectFormat");
    const dataRadioFormat = new FormData(formSelectFormat);
    var radioFormat = dataRadioFormat.get("radioFormat");
    var highlighter = $('#editable_marc').highlightTextarea({
        words: [{
            colour: 'red',
            words: ['^[^=<][^<]?[^<]?[^<]?',                                    //Field must be preceded by =
                '^=(?![A-Z0-9][A-Z0-9][A-Z0-9]\\b)[^<]?[^<]?[^<]?',             //Field tag must be three alphanumeric characters
                '^=[A-Z0-9][A-Z0-9][A-Z0-9](?!  )[^<]?[^<]?',                    //Field tag must be followed by two spaces
                '^=(?!(LDR|FMT|00[0-9]|019))([A-Z]{3}|[0-9]{3})  (?![0-9#][0-9#])[^<]?[^<]?',    //Indicators must be two numbers or # - EXCLUDE CONTROL FIELDS and 019
                '^=(019)  (?![0-9#a-z]#)[^<]?[^<]?',                                         //Indicators must be two numbers or # - EXCLUDE CONTROL FIELDS and 019
                '^=(?!(LDR|FMT|00[0-9]))([A-Z]{3}|[0-9]{3})  [0-9#][0-9#](?! )[^<]?',        //Indicators must be followed by a single space - EXCLUDE CONTROL FIELDS
                '^=(?!(LDR|FMT|00[0-9]))([A-Z]{3}|[0-9]{3})  [0-9#][0-9#] [^\\$]',           //Field must contain some subfields
                '^=(?:(LDR|FMT|00[0-9]))  [0-9#][0-9#] ',                                    //Control fields must not have indicators
                '^=(?:(LDR|FMT|00[0-9])).*\\$',                                              //Control fields must not have subfields
                '^=(?:(LDR|FMT|00[0-9]))  [A-Za-z0-9#\\|]*[^A-Za-z0-9#.\\|<>\\n\\r$]',       //Control fields must contain only alphanumeric characters, ., # or |
                '\\$([^\\$a-z0-9<]|$)',                                            //Subfield codes must be a-z or 0-9
                '\\$(?=\\n)',                                                   //Subfield codes must not occur at the end of a line
                ]
            }, {
            colour: 'orange',
            words: ['=100  .. \\$a[A-Z][A-Z][A-Z]+',                        //Main entry in capital letters
                '=008  ......\\|',                                          //No 008 date type
                '^=(260|720|653)',                                          //260 or 720 field
                '\\$emain entry',                                           //$emain entry
                '^=245[^\\n]*edition',                                      //'edition' in 245
                '\\|\\$u',
                'Another copy',
                '^=(009|011|090|091|211|212|214|241|265|301|302|303|304|305|308|315|350|359|440|503|512|517|523|527|537|543|570|582|590|590|652|705|715|755|840|851|870|871|872|873)'   // obsolete fields
                ]
            }, {
            colour: 'green',
            words: ['(\\$.|\\b)pp*\\b\\.?',
                '(\\$.|\\b)illu?s?\\b\\.?',
                '(\\$.|\\b)sh?\\b\\.?',
                '(\\$.|\\b)facsi?m?s?\\b\\.?',
                '(\\$.|\\b)geneal\\b\\.?',
                '(\\$.|\\b)ports?\\b\\.?',
                '(\\$.|\\b)col\\b\\.?',
                '(\\$.|\\b)mins?\\b\\.?',
                'Held in OIOC',]
        }],
        resizable: true
    });
}


async function checkRecord() {
    let data = new FormData();
    data.append("locked_marc", $('#locked_marc').val());
    data.append("editable_marc", $('#editable_marc').val());
    const resp = await fetch('validate', {
        'method': 'POST',
        'body': data
    });
    var ht = await resp.text()
    $('#validate').html($(ht));
}

/* END Functions for checking records */

/* Functions for record navigation */


async function nextRecord() {
    let data = new FormData();
    data.append('action',  'next');
    var resp = await fetch('next_record', {
        'method': 'POST',
        'body': data,
    });
    var ht = await resp.text()
    if (ht.startsWith('<p>End of file')) {
        console.log('EOF');
        $('#validate').html("");
        $('#marc').html($(ht));
    } else {
        $('#marc').html($(ht));
        setupToggle();
        setupHighlighter();
        checkRecord();
    };
}

async function nextRecordWithErrors() {
    let data = new FormData();
    data.append('action',  'next');
    var resp = await fetch('next_record_with_errors', {
        'method': 'POST',
        'body': data,
    });
    var ht = await resp.text()
    if (ht.startsWith('<p>End of file')) {
        console.log('EOF');
        $('#validate').html("");
        $('#marc').html($(ht));
    } else {
        $('#marc').html($(ht));
        setupToggle();
        setupHighlighter();
        checkRecord();
    };
}

/* END Functions for record navigation */