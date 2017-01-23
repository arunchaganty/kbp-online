//Add instructions to pages
function InstructionWidget( name, instructionsFile){
    this.name = name;
    this.instructionsFile = instructionsFile;
    this.parent_elem = $('body').append('<div/>');
    var self = this;
    $('#instructions').click(self.show.bind(self));
    this.elem = $('#modals').load('templates/instruction-modal.html', function(){
    self.elem = $('#instruction-widget-modal');
    self.elem.find('.modal-body').load(instructionsFile);
    self.elem.find('.submit').click(function(){
        self.doneListeners.forEach(function(cb) {cb();});
        self.hide();
    });
    self.showFirstTime();
      });
}
InstructionWidget.prototype.doneListeners = [];
InstructionWidget.prototype.showFirstTime = function(){
    console.log(Cookies.get(this.name+"_seen"));
    if(Cookies.get(this.name+"_seen") != 'True'){
        this.show();
    }
}
InstructionWidget.prototype.show = function(){
    this.elem.modal('show');
}
InstructionWidget.prototype.hide = function(mention){
    Cookies.set(this.name+'_seen', 'True');
    this.elem.modal('hide');
}

