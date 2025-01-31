$(document).ready(function () {
    const errors = $('template')[0].innerHTML;
    if (errors != '') {
        alert(errors);
    }
});