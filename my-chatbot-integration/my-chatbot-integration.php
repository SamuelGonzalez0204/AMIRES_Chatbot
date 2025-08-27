<?php
/*
Plugin Name: Mi Chatbot Integration
Description: Integra el chatbot de Myopia Magna con la API de Flask.
Version: 1.0
Author: Samuel González Martín
*/

if ( ! defined( 'ABSPATH' ) ) {
    exit;
}

function my_chatbot_enqueue_scripts() {
    wp_enqueue_script('jquery');

    wp_enqueue_script(
        'my-chatbot-script',
        plugin_dir_url( __FILE__ ) . 'js/chatbot.js', 
        array('jquery'), 
        '1.0', 
        true 
    );

    $current_user = wp_get_current_user();
    $user_id = $current_user->ID;
    $user_roles = (array) $current_user->roles;
    $is_editor_or_admin = in_array('editor', $user_roles) || in_array('administrator', $user_roles);
    $upload_nonce = wp_create_nonce('chatbot_upload_pdf');

    wp_localize_script(
        'my-chatbot-script',
        'myChatbotData',
        array(
            'apiUrl' => 'https://18.232.166.114/ask', 
            'uploadUrl' => 'https://18.232.166.114/upload_pdf', 
            'corsOrigin' => 'https://consultas.miopiamagna.org/',
            'userId' => $user_id,
            'canUpload' => $is_editor_or_admin,
            'uploadNonce' => $upload_nonce
        )
    );
    wp_enqueue_style(
        'my-chatbot-style',
        plugin_dir_url( __FILE__ ) . 'css/style.css', 
        array(), 
        '1.0', 
        'all'
    );
}
add_action( 'wp_enqueue_scripts', 'my_chatbot_enqueue_scripts' );

function my_chatbot_shortcode() {
    ob_start();
    $current_user = wp_get_current_user();
    $user_roles = (array) $current_user->roles;
    $is_editor_or_admin = in_array('editor', $user_roles) || in_array('administrator', $user_roles);
    ?>
    <div id="chatbot-container">
        <div id="chat-messages"></div>
        <input type="text" id="user-input" placeholder="Escribe tu pregunta...">
        <button id="send-button">Enviar</button>
        <hr>
        <?php if ( $is_editor_or_admin ) : ?>
            <h2>Subir PDF</h2>
            <input type="file" id="pdf-upload" accept=".pdf">
            <button id="upload-button">Subir PDF</button>
            <div id="upload-status"></div>
        <?php endif; ?>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode( 'my_chatbot', 'my_chatbot_shortcode' );

add_action('wp_ajax_nopriv_chatbot_validate_nonce', 'chatbot_validate_nonce_callback');
add_action('wp_ajax_chatbot_validate_nonce', 'chatbot_validate_nonce_callback');
function chatbot_validate_nonce_callback() {
    $nonce = $_POST['nonce'];
    if (wp_verify_nonce($nonce, 'chatbot_upload_pdf')) {
        echo 'valid';
    } else {
        echo 'invalid';
    }
    wp_die();
}