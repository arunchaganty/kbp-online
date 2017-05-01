$(window).on('beforeunload', function () {
  $("#document").scrollTop(0);
});

/*$(window).on('load', function () {
  $("#document").scrollTop(0);
    $('#document').bind('scroll', function(e){
      var elem = $(e.currentTarget);
        if((turkHelper == undefined || !turkHelper.activated || !turkHelper.preview) && mainInterface.minOutput()){
            $("#done")[0].disabled = false;
        }
    });
});*/

