const form = document.querySelector("#loginForm");
const usernameInput = document.querySelector("#usernameInput");
const passwordInput = document.querySelector("#passwordInput");
const rememberInput = document.querySelector("#rememberInput");
const togglePasswordButton = document.querySelector("#togglePasswordButton");
const formMessage = document.querySelector("#formMessage");
const forgotButton = document.querySelector("#forgotButton");
const forgotDialog = document.querySelector("#forgotDialog");
const forgotForm = document.querySelector("#forgotForm");
const forgotCloseButton = document.querySelector("#forgotCloseButton");
const forgotCancelButton = document.querySelector("#forgotCancelButton");
const recoverInput = document.querySelector("#recoverInput");
const recoverMessage = document.querySelector("#recoverMessage");

const params = new URLSearchParams(window.location.search);
const usernameFromUrl = params.get("merchant") || params.get("username") || "";
const passwordFromUrl = params.get("password") || "";
const savedUsername = localStorage.getItem("merchantLoginUsername") || "";

if (usernameFromUrl || savedUsername) {
  usernameInput.value = usernameFromUrl || savedUsername;
  rememberInput.checked = Boolean(savedUsername || usernameFromUrl);
}

if (passwordFromUrl) {
  passwordInput.value = passwordFromUrl;
}

togglePasswordButton.addEventListener("click", () => {
  const isPassword = passwordInput.type === "password";
  passwordInput.type = isPassword ? "text" : "password";
  togglePasswordButton.textContent = isPassword ? "隐藏" : "显示";
  togglePasswordButton.setAttribute("aria-label", isPassword ? "隐藏密码" : "显示密码");
});

form.addEventListener("submit", (event) => {
  event.preventDefault();
  const username = usernameInput.value.trim();
  const password = passwordInput.value.trim();

  if (!username) {
    showFormMessage("请输入商家用户名。");
    usernameInput.focus();
    return;
  }

  if (password.length < 6) {
    showFormMessage("密码至少需要 6 位字符。");
    passwordInput.focus();
    return;
  }

  if (rememberInput.checked) {
    localStorage.setItem("merchantLoginUsername", username);
  } else {
    localStorage.removeItem("merchantLoginUsername");
  }

  sessionStorage.setItem(
    "merchantLoginSession",
    JSON.stringify({ username, signedInAt: new Date().toISOString() })
  );
  showFormMessage("登录成功，正在进入商家运营工作台。", true);
  window.setTimeout(() => {
    window.location.href = `./merchant-dashboard.html?merchant=${encodeURIComponent(username)}`;
  }, 420);
});

forgotButton.addEventListener("click", () => {
  recoverInput.value = usernameInput.value.trim();
  recoverMessage.textContent = "";
  recoverMessage.classList.remove("is-success");
  if (typeof forgotDialog.showModal === "function") {
    forgotDialog.showModal();
  } else {
    forgotDialog.setAttribute("open", "");
  }
  recoverInput.focus();
});

forgotCloseButton.addEventListener("click", closeForgotDialog);
forgotCancelButton.addEventListener("click", closeForgotDialog);

forgotForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const account = recoverInput.value.trim();
  if (!account) {
    recoverMessage.textContent = "请输入账号或手机号。";
    recoverMessage.classList.remove("is-success");
    recoverInput.focus();
    return;
  }
  recoverMessage.textContent = "重置指引已发送，请查看绑定手机号或商家后台通知。";
  recoverMessage.classList.add("is-success");
});

function closeForgotDialog() {
  if (forgotDialog.open) {
    forgotDialog.close();
  }
}

function showFormMessage(message, isSuccess = false) {
  formMessage.textContent = message;
  formMessage.classList.toggle("is-success", isSuccess);
}
