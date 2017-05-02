/*!
 * KBPOnline: mechanical turk helper script.
 * Author: Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery'], function($) {

    // Gets the URL variables stored in the GET string.
    function getURLVars() {
        var vars = {}, hash;
        var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');
        for(var i = 0; i < hashes.length; i++) {
            hashes[i] = decodeURIComponent(hashes[i]);
            hash = hashes[i].split('=');
            vars[hash[0]] = hash[1];
        }
        return vars;
    }

    // Sets up submit form to interact with mturk
    function TurkHelper() {
        // Records start time
        st = new Date().getTime()/1000;

        this.urlVars = getUrlVars();
        this.activated = false;
        if ('assignmentId' in this.urlVars) {
            this.activated = true;
        }
        else {
            return;
        }
        this.preview = true;
        if (this.urlVars.assignmentId != 'ASSIGNMENT_ID_NOT_AVAILABLE') {
            this.preview = false;
        }
        if (this.activated) {
            var submitUrl = "";
            if (this.preview) {
                $("#done")[0].disabled = true;
                return;
            }
            if ('target' in this.urlVars) {
                if (this.urlVars.target == 'sandbox') {
                    submitUrl = "https://workersandbox.mturk.com/mturk/externalSubmit";
                }
                else if (this.urlVars.target == 'actual') {
                    submitUrl = "https://www.mturk.com/mturk/externalSubmit";
                }
            }

            $('#mturk_form').attr('action', submitUrl);
            $("#assignmentId").attr('value', this.urlVars.assignmentId);
            $("#docId").attr('value', this.urlVars.doc_id);
            console.log('all ready to submit');
        }
    }

    TurkHelper.prototype.initialize_doc = function(doc_id) {
        $.getJSON(doc_id, initialize_interface)
            .fail(function() {
                console.log("Could not load data.");
            });
    };

    return TurkHelper;
});
