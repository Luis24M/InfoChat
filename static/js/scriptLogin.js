document.addEventListener("DOMContentLoaded", function() {
  const form = document.querySelector('form');
  const emailInput = document.querySelector('input[type="text"]');
  const passwordInput = document.querySelector('input[type="password"]');
  const errorMessage = document.getElementById('error-message');

  form.addEventListener('submit', async (event) => {
    event.preventDefault();

    const email = emailInput.value;
    const password = passwordInput.value;

    try {
      const response = await axios.post('http://127.0.0.1:5000/login', { username_or_email: email, password });

      if (response.data.message === 'Login successful') {
        // Guardar el token de autenticación en el cliente (por ejemplo, en localStorage)
        localStorage.setItem('token', response.data.token);

        // Redirigir al usuario a la página protegida
        window.location.href = '/chat';
      } else {
        showErrorMessage('Invalid email or password');
      }
    } catch (error) {
      showErrorMessage('Error de conexión');
    }
  });

  function showErrorMessage(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
    errorMessage.style.opacity = '1';
    errorMessage.style.color = 'white';
    errorMessage.style.paddingBottom = '20px';
    errorMessage.style.textAlign = 'center';
  }
});
