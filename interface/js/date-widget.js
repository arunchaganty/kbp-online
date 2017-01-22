
//Cannonicalize dates
function DateWidget(callback){
    this.callback = callback;
    var _this = this;
    $('#submit-wiki-search').click(function(){_this.populate(this.form.search_input.value);});
    $('#no-wiki-link').click(function(){_this.callback();});
    $('input[type=radio][name=week-or-date]').change(function() {
        if (this.value == 'day') {
            $('input[name=month]').prop('disabled', true);
            $('input[name=day]').prop('disabled', true);
            $('input[name=week]').prop('disabled', false);
        }
        else if (this.value == 'week') {
            $('input[name=month]').prop('disabled', false);
            $('input[name=day]').prop('disabled', false);
            $('input[name=week]').prop('disabled', true);
        }
    });
}
