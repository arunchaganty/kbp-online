/*!
 * KBPOnline
 * Author: Arun Chaganty, Ashwin Paranjape
 * Licensed under the MIT license
 */

define(['jquery', 'moment/moment', 'bootstrap', '../util'], function($, moment, _, util) {
  // Canonicalize dates
  function DateModal(cb) {
    var self = this;

    util.getDOMFromTemplate('/static/kbpo/html/DateModal.html', function(elem) {
      self.elem = elem;
      self.elem.find('input[type=radio][name=week-or-date]').change(function() {
        if (this.value == 'week') {
          self.elem.find('select[name=month]').prop('disabled', true);
          self.elem.find('select[name=day]').prop('disabled', true);
          self.elem.find('select[name=week]').prop('disabled', false);
        }
        else if (this.value == 'day') {
          self.elem.find('select[name=month]').prop('disabled', false);
          self.elem.find('select[name=day]').prop('disabled', false);
          self.elem.find('select[name=week]').prop('disabled', true);
        }
        else 
          //if (this.value == 'neither') 
        {
          self.elem.find('select[name=month]').prop('disabled', true);
          self.elem.find('select[name=day]').prop('disabled', true);
          self.elem.find('select[name=week]').prop('disabled', true);
        }
      });
      self.elem.find('input[type=radio][name=week-or-date][value=day]').click();
      self.monthSelect = self.elem.find('select[name=month]');
      self.weekSelect = self.elem.find('select[name=week]');
      self.daySelect = self.elem.find('select[name=day]');
      self.yearSelect = self.elem.find('select[name=year]');
      self.elem.find('#link-date-submit').click(function(){
        self.done();
      });

      cb(elem);
    });
  }
  DateModal.prototype.doneListeners = [];

  DateModal.prototype.setDocDate = function(docdate){
    var parsedDocdate = moment();
    if(docdate !== undefined) {
      var _parsedDocdate = moment(docdate);
      if (_parsedDocdate._isValid){
        parsedDocdate = _parsedDocdate;
        this.docdate = parsedDocdate;
      }
    }
    this.elem.find('#doc-date').text(this.docdate.format("dddd, MMMM Do YYYY"));
  };

  DateModal.prototype.show = function(mentionGloss, suggestion){
    var parsedSuggestion;
    if(suggestion !== undefined && suggestion.match('X') === null){
      // using .utc handles the edge condition where 'Tuesday' is
      // taken to be 00:00 (timezone), but when rendered, gets
      // reweinded.
      var _parsedSuggestion = moment.utc(suggestion);
      console.info("Attempting to set suggested date", suggestion, "found", _parsedSuggestion);
      if (_parsedSuggestion._isValid){
        parsedSuggestion = _parsedSuggestion;
      }
    }
    this.refresh(parsedSuggestion);
    this.elem.find('#date-gloss').text(mentionGloss);
    $('#date-widget-modal').modal('show');
  };

  DateModal.prototype.done = function() {
    var self = this;
    $('#date-widget-modal').modal('hide').on('hidden.bs.modal', function() {
      var link = self.getSelectedDateString();
        self.doneListeners.forEach(function(cb_) {cb_(link);});
    });
  };

  DateModal.prototype.refreshDays = function(){
    var date = this.getSelectedDate();
    this.daySelect.find('option').remove();
    this.daySelect.append($("<option />").val('NA').text('NA'));

    var i;
    if (this.monthSelect.val()=='NA' || this.yearSelect.val()=='NA') {
      for(i=1; i<=date.daysInMonth(); i++) {
        this.daySelect.append($("<option />").val(i).text(date.clone().date(i).format('DD')));
      }
    } else {
      for(i=1; i<=date.daysInMonth(); i++){
        this.daySelect.append($("<option />").val(i).text(date.clone().date(i).format('dddd, DD')));
      }
    }
    if(date.month()==moment().month() && date.year() == moment().year()) {
      ////this.daySelect.find('option[value='+moment().date()+']').attr("selected", true);
    } else {
      //this.daySelect.find('option[value='+date.date()+']').attr("selected", true).addClass('date-now');
      if (this.docdate !== undefined) {
        this.daySelect.find('option[value='+this.docdate.date()+']').addClass('date-now');
      }
    }
  };

  DateModal.prototype.getSelectedDate = function(){
    var selectedDate = moment();
    if(this.yearSelect.val() != 'NA'){
      selectedDate.year(this.yearSelect.val());
    }
    if (this.elem.find('input[type=radio][name=week-or-date]:checked').val() == "week"){
      if(this.weekSelect.val() != 'NA'){
        selectedDate.week(this.weekSelect.val());
      } 
    }else{
      if(this.monthSelect.val() != 'NA'){
        selectedDate.month(this.monthSelect.val()-1);
      } 
      if(this.daySelect.val() != 'NA'){
        selectedDate.date(this.daySelect.val());
      } 
    }   
    return selectedDate;
  };
  DateModal.prototype.getSelectedDateString = function(){
    var selectedDate = this.getSelectedDate();
    var dateStr = "";
    if(this.yearSelect.val() != 'NA'){
      dateStr+=selectedDate.format('YYYY-');
    }else{
      dateStr+='XXXX-';
    }
    if (this.elem.find('input[type=radio][name=week-or-date]:checked').val() == "week"){
      if(this.weekSelect.val() != 'NA'){
        dateStr +='W'+selectedDate.format('WW');
      } else{
        dateStr +='WXX';
      }
    }else{
      if(this.monthSelect.val() != 'NA'){
        dateStr += selectedDate.format('MM')+'-';
      } else{
        dateStr +='XX-';
      }
      if(this.daySelect.val() != 'NA'){
        dateStr += selectedDate.format('DD');
      } else{
        dateStr +='XX';
      }
    }   
    return dateStr;
  };

  DateModal.prototype.refresh = function(date){
    this.elem.find('.date-now').removeClass('date-now');
    //this.elem.find(':selected').each(function(elem){$(elem).prop("selected", false);});

    this.monthSelect.find('option').remove();
    this.weekSelect.find('option')./*not('[value=NA]').*/remove();
    this.yearSelect.find('option')./*not('[value=NA]').*/remove();

    this.monthSelect.append($("<option />").val('NA').text('NA'));
    this.weekSelect.append($("<option />").val('NA').text('NA'));
    this.yearSelect.append($("<option />").val('NA').text('NA'));

    var months = moment.monthsShort();
    var i;
    for(i=1; i<=12;i++){ 
      this.monthSelect.append($("<option />").val(i).text(months[i-1]));
    }
    for(i=1; i<=53;i++){
      this.weekSelect.append($("<option />").val(i).text(i));
    }
    for(i=2017; i>=1900;i--){
      this.yearSelect.append($("<option />").val(i).text(i));
    }
    this.monthSelect.change($.proxy(this.refreshDays, this));
    this.yearSelect.change($.proxy(this.refreshDays, this));
    if (date === undefined){
      if (this.docdate === undefined){
        date=moment();
      }
      else{
        date = this.docdate;
      }
    }   

    this.monthSelect.find('option[value='+(date.month()+1)+']').attr("selected", true);
    this.weekSelect.find('option[value='+date.week()+']').attr("selected", true);
    this.yearSelect.find('option[value='+date.year()+']').attr("selected", true);
    this.refreshDays();
    this.daySelect.find('option[value='+date.date()+']').attr("selected", true);
    if(this.docdate !== undefined){
      this.monthSelect.find('option[value='+(this.docdate.month()+1)+']').addClass('date-now');
      this.weekSelect.find('option[value='+(this.docdate.week())+']').addClass('date-now');
      this.yearSelect.find('option[value='+(this.docdate.year())+']').addClass('date-now');
    }
  };

  return DateModal;
});
