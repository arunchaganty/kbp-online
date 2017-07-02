/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', 'bootstrap', '/static/js-cookie/src/js.cookie.js'], function($, _, Cookies) {
    function InstructionWidget(name, instructionsFile) {
        this.name = name;
        this.instructionsFile = instructionsFile;
        this.parent_elem = $('body').append('<div/>');
        var self = this;
        $('#instructions').click(self.show.bind(self));
        this.elem = $('#modals').load('/static/kbpo/html/InstructionsModal.html', function(){
        self.elem = $('#instruction-widget-modal');
        self.elem.find('.modal-body').load(instructionsFile);
        self.elem.find('#instruction-widget-continue').click(function(){
            self.doneListeners.forEach(function(cb) {cb();});
            self.hide();
        });
        self.showFirstTime();
          });
    }
    InstructionWidget.prototype.doneListeners = [];
    InstructionWidget.prototype.showFirstTime = function(){
        console.log(Cookies.get(this.name+"_seen_1"));
        if(Cookies.get(this.name+"_seen") != 'True'){
            this.show();
        }
    };
    InstructionWidget.prototype.show = function(){
        this.elem.modal('show');
        return false;
    };
    InstructionWidget.prototype.hide = function(mention){
        Cookies.set(this.name+'_seen', 'True');
        this.elem.modal('hide');
    };

    return InstructionWidget;
});
