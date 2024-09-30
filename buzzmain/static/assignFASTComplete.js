function autoSubject(request, response, responseStyle, currentSuggestIndex) {
    var requestterm = request.term;
    requestterm = requestterm.replace(/\-|\(|\)|:/g, "");
    requestterm = requestterm.replace(/ /g, "%20");

    var suggestIndex = currentSuggestIndex;
    var url = 'http://fast.oclc.org/searchfast/fastsuggest?&query=' + requestterm + '&queryIndex=' + suggestIndex + '&queryReturn=suggestall%2Cidroot%2Cauth%2Ctag%2Ctype%2Craw%2Cbreaker%2Cindicator&suggest=autoSubject'

    if(location.protocol == "https:") {
	 	url = url.replace(/http:/,"https:");
	 }	

    $.ajax({
        type: "GET",
        headers: {'Access-Control-Allow-Origin':'*'},
        url: url,
        dataType: "JSONP",
        jsonp: 'json.wrf',
        success: function (data) {

            var mr = [];
            var result = data.response.docs;

            for (var i = 0, len = result.length; i < len; i++) {
               
               var term = result[i]['suggestall'];
               var useValue = breakerStyle(result[i]);
						
                mr.push({
                    label: term,                       //heading matched on 
                    value: useValue,                   //this gets inserted to the search box when an autocomplete is selected,
                    idroot: result[i]["idroot"],       //the fst number
                    auth: result[i]["auth"],           //authorized form of the heading, viewable -- format
                    tag: result[i]["tag"],             //heading tag, 1xx
                    type: result[i]["type"],           //auth= term is authorized form, alt= term is alternate (see also) form
                    raw: result[i]["raw"],             //authorized form of the heading, $a-z subdivision form
                    breaker: result[i]["breaker"],     //authorized form of the heading, marcbreaker coding for diacritics
                    indicator: result[i]["indicator"]  //heading first indicator 
                });
            }
            console.log(mr);
            response(mr);
        }
    });
}

function breakerStyle(res) {
   var text = res["raw"];           //empty if no diacritics
   /*if(text == "") text = res["raw"];    //empty if no subfields*/
   if(text == "") text = res["auth"];   //default view for simple cases
   var result = "="+(res["tag"]+500) + "  " + res["indicator"].replace(' ', '#') + "7 $a" + text + ".$2fast"+"$0(OCoLC)"+res["idroot"] ;
   return result;
}

function htmlDecode(input){
  var e = document.createElement('div');
  e.innerHTML = input;
  return e.childNodes.length === 0 ? "" : e.childNodes[0].nodeValue;
}
