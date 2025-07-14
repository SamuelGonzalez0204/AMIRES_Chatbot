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

    wp_localize_script(
        'my-chatbot-script',
        'myChatbotData',
        array(
            'apiUrl' => 'http://3.88.214.117:8000/ask', 
            'uploadUrl' => 'http://3.88.214.117:8000/upload_pdf', 
            'corsOrigin' => 'http://consultas.miopiamagna.org/' 
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
    ?>
    <div id="chatbot-container">
        <div id="chat-messages"></div>
        <input type="text" id="user-input" placeholder="Escribe tu pregunta...">
        <button id="send-button">Enviar</button>
        <hr>
        <h2>Subir PDF</h2>
        <input type="file" id="pdf-upload" accept=".pdf">
        <button id="upload-button">Subir PDF</button>
        <div id="upload-status"></div>
    </div>
    <?php
    return ob_get_clean();
}
add_shortcode( 'my_chatbot', 'my_chatbot_shortcode' );