$(document).ready(function()
{
	$(".pass_select").each(function()
	{
		if ($(this).hasClass("select_initially_passed"))
		{
			$(this).val("passed")
			$(this).addClass("passed")
			$(this).removeClass("failed")
		}
		else
		{
			$(this).val("failed")
			$(this).addClass("failed")
			$(this).removeClass("passed")
		}
	});

	$(".pass_select").change(function()
	{
		if ($('option:selected', this).hasClass("passed"))
		{
			$(this).addClass("passed")
			$(this).removeClass("failed")
		}
		else
		{
			$(this).addClass("failed")
			$(this).removeClass("passed")
		}
	});

	$("#print_button").click(function()
	{
		window.print();
	});

    $("#csv_button").click(function () {
        window.open(window.location.href.split('?')[0] + '/csv');
    });

    $("#json_button").click(function () {
        window.open(window.location.href.split('?')[0] + '/json');
    });

    $("#raw_button").click(function () {
        window.open(window.location.href.split('?')[0] + '/raw_csv');
    });
});
