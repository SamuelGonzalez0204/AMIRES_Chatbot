jQuery(document).ready(function($) {
    const API_URL = myChatbotData.apiUrl;
    const UPLOAD_URL = myChatbotData.uploadUrl;
    const CORS_ORIGIN = myChatbotData.corsOrigin;
    const USER_ID = myChatbotData.userId;
    const CAN_UPLOAD = myChatbotData.canUpload;
    const UPLOAD_NONCE = myChatbotData.uploadNonce;

    const chatMessages = $('#chat-messages');
    const userInput = $('#user-input');
    const sendButton = $('#send-button');
    const pdfUploadInput = $('#pdf-upload');
    const uploadButton = $('#upload-button');
    const uploadStatus = $('#upload-status');

    // Ocultar área de subida si no tiene permiso (por seguridad extra)
    if (!CAN_UPLOAD) {
        $('#pdf-upload, #upload-button, #upload-status').hide();
        $('h2:contains("Subir PDF")').hide();
    }

    function addMessage(sender, message) {
        chatMessages.append(`<p><strong>${sender}:</strong> ${message}</p>`);
        chatMessages.scrollTop(chatMessages[0].scrollHeight); 
    }

    sendButton.on('click', function() {
        const question = userInput.val().trim();
        if (question === '') {
            return;
        }

        addMessage('Tú', question);
        userInput.val('');
        sendButton.prop('disabled', true).text('Pensando...'); 

        $.ajax({
            url: API_URL,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify({ question: question }),
            success: function(response) {
                addMessage('Chatbot', response.answer);
            },
            error: function(xhr, status, error) {
                console.error('Error al comunicarse con el chatbot:', error);
                addMessage('Chatbot', 'Lo siento, hubo un error al obtener la respuesta.');
            },
            complete: function() {
                sendButton.prop('disabled', false).text('Enviar');
            }
        });
    });

    userInput.on('keypress', function(e) {
        if (e.which === 13) { 
            sendButton.click();
        }
    });

    uploadButton.on('click', function() {
        const file = pdfUploadInput[0].files[0];
        if (!file) {
            uploadStatus.text('Por favor, selecciona un archivo PDF.').css('color', 'orange');
            return;
        }

        uploadStatus.text('Subiendo...').css('color', 'blue');
        uploadButton.prop('disabled', true);

        const formData = new FormData();
        formData.append('pdf_file', file);
        formData.append('user_id', USER_ID);
        formData.append('wp_nonce', UPLOAD_NONCE);

        $.ajax({
            url: UPLOAD_URL,
            type: 'POST',
            data: formData,
            processData: false, 
            contentType: false, 
            success: function(response) {
                uploadStatus.text('Subida exitosa: ' + response.message + (response.news_id ? ' ID: ' + response.news_id : '')).css('color', 'green');
                pdfUploadInput.val(''); 
            },
            error: function(xhr, status, error) {
                const errorMessage = xhr.responseJSON && xhr.responseJSON.error ? xhr.responseJSON.error : 'Error desconocido al subir el PDF.';
                uploadStatus.text('Error en la subida: ' + errorMessage).css('color', 'red');
                console.error('Error al subir PDF:', error, xhr.responseText);
            },
            complete: function() {
                uploadButton.prop('disabled', false);
            }
        });
    });
});