document.addEventListener("DOMContentLoaded", function() {
  var chatLog = document.getElementById("chat-log");
  var userInput = document.getElementById("user-input");
  var loginForm = document.getElementById("login-form");

  // Presentación inicial del asistente
  var assistantMessage = document.createElement("div");
  assistantMessage.classList.add("reply");
  assistantMessage.textContent = "¡Hola! Soy InfoChat. ¿En qué puedo ayudarte?";
  chatLog.appendChild(assistantMessage);

  // Manejo del envío de mensajes del usuario
  userInput.addEventListener("keydown", function(event) {
    if (event.key === "Enter" && userInput.value !== "") {
      var message = document.createElement("div");
      message.classList.add("message");
      message.textContent = userInput.value;
      chatLog.appendChild(message);
      chatLog.scrollTop = chatLog.scrollHeight;

      var query = userInput.value;

      userInput.value = "";

      var xhr = new XMLHttpRequest();
      xhr.open("POST", "/chat", true);
      xhr.setRequestHeader("Content-Type", "application/json");
      xhr.onreadystatechange = function() {
        if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
          var response = JSON.parse(xhr.responseText);

          setTimeout(function() {
            var reply = document.createElement("div");
            reply.classList.add("reply");

            function formatEmails(text) {
              return text.replace(/([^\s]+@[^\s]+\.[^\s]+)/g, '<a href="mailto:$1">$1</a>');
            }

            var formattedResponse = formatEmails(response.message);
            
            // Verificar si la respuesta contiene una lista
            if (formattedResponse.includes("-")) {
              var paragraphs = formattedResponse.split(/- (.+)/);
              if (paragraphs.length > 1) {
                reply.innerHTML = paragraphs[0] + "</p><p>" + paragraphs[1];
              } else {
                reply.innerHTML = formattedResponse;
              }
            } else {
              reply.innerHTML = formattedResponse;
            }

            // Realizar otros formatos si es necesario, como listas o enlaces web
            if (formattedResponse.includes(".")) {
              reply.innerHTML = formattedResponse.replace(/\./g, ".<br><br>");
            }
            if (formattedResponse.includes("-")) {
              reply.innerHTML = formattedResponse.replace(/- /g, "<br>- ");
            }
            if (formattedResponse.includes("1.")) {
              reply.innerHTML = formattedResponse.replace(/\d+\./g, "<br>$&");
            }
            if (formattedResponse.includes("www")) {
              reply.innerHTML = formattedResponse.replace(/(www\..+?)(?:\s|$)/g, '<a href="http://$1" target="_blank">$1</a>');
            }

            chatLog.appendChild(reply);
            chatLog.scrollTop = chatLog.scrollHeight;
          }, 0);
        }
      };

      xhr.send(JSON.stringify({ query: query }));
    }
  });
});
