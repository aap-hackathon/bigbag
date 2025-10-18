document.addEventListener("DOMContentLoaded", function () {
  const form = document.getElementById("signupForm");
  if (!form) return;

  // helper to create or return error element for a field
  function getErrorEl(input) {
    let el = input.nextElementSibling;
    if (el && el.classList && el.classList.contains("field-error")) return el;
    el = document.createElement("div");
    el.className = "field-error";
    input.parentNode.insertBefore(el, input.nextSibling);
    return el;
  }

  function clearError(input) {
    const el = input.nextElementSibling;
    if (el && el.classList && el.classList.contains("field-error"))
      el.textContent = "";
  }

  function setError(input, msg) {
    const el = getErrorEl(input);
    el.textContent = msg;
  }

  function validateField(input) {
    const name = input.name;
    const v = (input.value || "").trim();
    if (name === "pesel") {
      if (!/^[0-9]{11}$/.test(v))
        return "PESEL musi zawierać dokładnie 11 cyfr";
    }
    if (name === "first_name") {
      if (v.length < 2) return "Imię musi mieć minimum 2 znaki";
    }
    if (name === "last_name") {
      if (v.length < 2) return "Nazwisko musi mieć minimum 2 znaki";
    }
    if (name === "phone_number") {
      if (!/^[0-9+\-\s]{9,}$/.test(v))
        return "Numer telefonu nie jest poprawny";
    }
    if (name === "email") {
      // basic structure check (local@domain)
      if (!/^[^\s@]+@[^\s@]+$/.test(v)) return "Podaj poprawny adres e-mail";
      const parts = v.split("@");
      if (parts.length !== 2) return "Podaj poprawny adres e-mail";
      const [local, domain] = parts;
      // no leading/trailing dot in local or domain
      if (
        local.startsWith(".") ||
        local.endsWith(".") ||
        domain.startsWith(".") ||
        domain.endsWith(".")
      )
        return "E-mail nie może zaczynać ani kończyć się kropką";
      // no consecutive dots anywhere in local or domain
      if (local.includes("..") || domain.includes(".."))
        return "E-mail nie może zawierać podwójnych kropek";
      // domain must contain at least one dot (e.g. example.com)
      if (domain.indexOf(".") === -1)
        return "Domena e-mail musi zawierać kropkę (np. example.com)";
    }
    if (name === "birth_date") {
      if (!v) return "Podaj datę urodzenia";
      const d = new Date(v);
      if (!d.getTime || isNaN(d.getTime())) return "Niepoprawna data";
      const today = new Date();
      if (d >= today) return "Data nie może być z przyszłości";
      const age = today.getFullYear() - d.getFullYear();
      if (age < 18) return "Musisz mieć co najmniej 18 lat";
    }
    if (name === "reg_address") {
      if (v.length < 5) return "Adres jest za krótki";
    }
    if (name === "nip") {
      if (v && !/^[0-9]{10}$/.test(v)) return "NIP musi mieć 10 cyfr";
    }
    return "";
  }

  // attach input listeners
  const inputs = form.querySelectorAll("input[name]");
  inputs.forEach(function (inp) {
    inp.addEventListener("input", function () {
      clearError(inp);
    });
    inp.addEventListener("blur", function () {
      const err = validateField(inp);
      if (err) setError(inp, err);
      else clearError(inp);
    });
  });

  // capture-phase submit handler to stop other scripts
  form.addEventListener(
    "submit",
    function (e) {
      // run validations
      let firstError = null;
      inputs.forEach(function (inp) {
        // skip checkbox
        if (inp.type === "checkbox") return;
        const err = validateField(inp);
        if (err) {
          setError(inp, err);
          if (!firstError) firstError = inp;
        } else {
          clearError(inp);
        }
      });

      const resident = document.getElementById("isResident");
      if (!resident || !resident.checked) {
        // create a virtual error under the checkbox
        let el = document.querySelector(".checkbox-inline .field-error");
        if (!el) {
          el = document.createElement("div");
          el.className = "field-error";
          const chk = document.querySelector(".checkbox-inline");
          if (chk) chk.appendChild(el);
        }
        el.textContent = "Musisz potwierdzić, że jesteś mieszkańcem";
        if (!firstError) firstError = resident;
      } else {
        const el = document.querySelector(".checkbox-inline .field-error");
        if (el) el.textContent = "";
      }

      if (firstError) {
        e.preventDefault();
        e.stopImmediatePropagation();
        e.stopPropagation();
        firstError.focus && firstError.focus();
        return;
      }

      // all good — prevent actual submit and log data
      e.preventDefault();
      e.stopImmediatePropagation();
      e.stopPropagation();

      const data = {};
      inputs.forEach(function (inp) {
        if (inp.type === "checkbox") return;
        data[inp.name] = inp.value;
      });
      data.isResident = (document.getElementById("isResident") || {}).checked;

      console.log("=== Signup validated data ===");
      console.log(data);
      console.log("============================");

      // show a small success message (insert below form)
      let note = form.querySelector(".form-success");
      if (!note) {
        note = document.createElement("div");
        note.className = "form-success";
        form.appendChild(note);
      }
      note.textContent = "Walidacja zakończona sukcesem!";

      // submit
      form.submit();
    },
    true,
  ); // use capture so we run before other listeners
});

