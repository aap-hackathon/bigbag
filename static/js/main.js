document.addEventListener('DOMContentLoaded', function(){
  // Modal-based login (legacy) — only wire if elements exist
  const modal = document.getElementById('loginModal');
  if(modal){
    const loginBtn = document.getElementById('loginBtn');
    const closeModal = document.getElementById('closeModal');
    const cancelBtn = document.getElementById('cancelBtn');

    function open() { modal.setAttribute('aria-hidden','false'); document.body.style.overflow = 'hidden'; }
    function close(){ modal.setAttribute('aria-hidden','true'); document.body.style.overflow = ''; }

    if(loginBtn) loginBtn.addEventListener('click', open);
    if(closeModal) closeModal.addEventListener('click', close);
    if(cancelBtn) cancelBtn.addEventListener('click', close);

    modal.addEventListener('click', function(e){ if(e.target === modal) close(); });
  }

  // Login form handling (works on both modal form and standalone login page)
  const form = document.getElementById('loginForm');
  if(form){
    form.addEventListener('submit', function(e){
      e.preventDefault();
      const email = form.email.value || form.querySelector('[name="email"]').value;
      // Demo behaviour: show alert in Polish
      alert('Zalogowano: ' + email + '\n(To jest demo — nie wysyła danych)');
      // If modal exists, close it
      if(modal) modal.setAttribute('aria-hidden','true');
    });
  }

  // Signup demo handling
  const signup = document.getElementById('signupForm');
  if(signup){
    signup.addEventListener('submit', function(e){
      e.preventDefault();
      const isResident = signup.querySelector('#isResident');
      if(!isResident || !isResident.checked){
        alert('Rejestracja jest dostępna tylko dla mieszkańców. Proszę potwierdzić, że jesteś mieszkańcem.');
        return;
      }
      const email = signup.email.value || signup.querySelector('[name="email"]').value;
      alert('Konto utworzone (demo): ' + email + '\nSprawdź skrzynkę e-mail dla dalszych informacji.');
    });
  }

  // Staff login demo handling
  const staff = document.getElementById('staffForm');
  if(staff){
    staff.addEventListener('submit', function(e){
      e.preventDefault();
      const email = staff.email.value || staff.querySelector('[name="email"]').value;
      alert('Zalogowano jako pracownik (demo): ' + email);
    });
  }

  // Staff login form (demo)
  const staffForm = document.getElementById('staffForm');
  if(staffForm){
    staffForm.addEventListener('submit', function(e){
      e.preventDefault();
      const email = staffForm.staffEmail.value;
      alert('Zalogowano jako pracownik: ' + email + '\n(To jest demo — nie wysyła danych)');
    });
  }

  // Signup form (resident-only) demo check
  const signupForm = document.getElementById('signupForm');
  if(signupForm){
    signupForm.addEventListener('submit', function(e){
      e.preventDefault();
      const resident = document.getElementById('isResident');
      if(!resident || !resident.checked){
        alert('Rejestracja dostępna tylko dla mieszkańców. Zaznacz pole potwierdzające.');
        return;
      }
      const email = signupForm.signupEmail.value;
      alert('Konto utworzone: ' + email + '\n(To jest demo — nie tworzy konta na serwerze)');
    });
  }
});
