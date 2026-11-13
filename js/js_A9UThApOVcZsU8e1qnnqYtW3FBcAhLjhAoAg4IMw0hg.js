//This script changes image on mousehover

$(".artistliste").hover(function() {
    $(this).find(".artist-hover").fadeIn();
  },
  function() {
    $(this).find(".artist-hover").fadeOut();
  });;
