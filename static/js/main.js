document.addEventListener('DOMContentLoaded', function() {
    const rsvpButtons = document.querySelectorAll('.rsvp-btn');

    rsvpButtons.forEach(button => {
        button.addEventListener('click', function() {
            const eventId = this.getAttribute('data-event-id');
            const rsvpModal = new bootstrap.Modal(document.getElementById('rsvpModal'));
            
            document.getElementById('rsvpYesBtn').onclick = function() {
                postRsvp(eventId, 'Going');
            };
            
            document.getElementById('rsvpMaybeBtn').onclick = function() {
                postRsvp(eventId, 'Maybe');
            };

            rsvpModal.show();
        });
    });

    function postRsvp(eventId, status) {
        fetch(`/rsvp/${eventId}/${status}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        })
        .then(response => response.json()) 
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.reload();
            } else {
                alert(data.message);  
            }
        })
        .catch(error => {
            alert('An error occurred. Please try again.');
            console.error('Error:', error);
        });
    }

    var flashMessage = document.getElementById('flashMessage');
    if (flashMessage) {
        flashMessage.style.display = 'block';
        setTimeout(function () {
            flashMessage.style.top = '0';
        }, 100); 

        setTimeout(function () {
            flashMessage.style.top = '-100px'; 
        }, 3000); 
    }

    if (document.body.getAttribute('data-event-created') === 'true') {
        var successModal = new bootstrap.Modal(document.getElementById('successModal'));
        successModal.show();
    }
});

document.addEventListener('DOMContentLoaded', function () {
    var commentModal = document.getElementById('commentModal');
    commentModal.addEventListener('show.bs.modal', function (event) {
        var button = event.relatedTarget;
        var eventId = button.getAttribute('data-event-id');
        var form = document.getElementById('commentForm');
        form.action = `/add_comment/${eventId}`;
    });
});
function toggleMenu() {
    document.getElementById("sideMenu").style.width = "250px";
}

function closeMenu() {
    document.getElementById("sideMenu").style.width = "0";
}
