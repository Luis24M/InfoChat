document.addEventListener("DOMContentLoaded", function() {
    const form = document.querySelector('form');
    const usernameInput = document.querySelector('input[type="username"]');
    const emailInput = document.querySelector('input[type="email"]');
    const passwordInput = document.querySelector('input[type="password"]');
    const confirmPasswordInput = document.querySelector('input[name="confirm-password"]');
    const errorMessage = document.getElementById('error-message');
  
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
  
      const username = usernameInput.value;
      const email = emailInput.value;
      const password = passwordInput.value;
      const confirmPassword = confirmPasswordInput.value;
  
      if (password !== confirmPassword) {
        showErrorMessage('Las contraseñas no coinciden');
        return;
      }
  
      try {
        const response = await axios.post('http://127.0.0.1:5000/register', {
          username,
          email,
          password
        });
  
        if (response.data.message === 'Las contraseñas no coinciden') {
          showErrorMessage('Las contraseñas no coinciden');
        } else if (response.data.message === 'Username already exists') {
          showErrorMessage('El nombre de usuario ya existe');
        } else if (response.data.message === 'Email already exists') {
          showErrorMessage('El email ya existe');
        } else {
          // Registro exitoso, redirigir al usuario a otra página
          window.location.href = '/';
        }
      } catch (error) {
        console.log(error);
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
  
  