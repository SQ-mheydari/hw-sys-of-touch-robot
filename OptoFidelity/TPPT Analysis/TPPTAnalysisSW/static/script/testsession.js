$(document).ready(function () {
    function notesSaved(data) {
        //alert(data);
        $('#notes').html(data);
        $("#notes").show();
        $("#notes_editor").hide();
        $("#notes_edit").show();
        $("#notes_save").hide();
    }

    function notesError() {
        alert('Saving of notes failed');
    }

    $(".test_row").click(function () {
        window.location = "/tests/" + $(this).data("test-id");
    });

    $("#notes_save").click(function () {
        var data = { command: 'set_notes',
            value: $('#notes_editor').val()
        };
        $.ajax({ type: "POST",
            data: { data: JSON.stringify(data)
            },
            datatype: 'text'
        }).done(notesSaved).fail(notesError);
    });

    $("#notes_edit").click(function () {
        $("#notes").hide();
        $("#notes_editor").show();
        $("#notes_edit").hide();
        $("#notes_save").show();
    });
});
