/**
 * Dashboard & Navigation Client Script
 */

document.addEventListener("DOMContentLoaded", () => {
  // Format room code input automatically to uppercase
  const roomCodeInputs = document.querySelectorAll(".room-code-input");
  roomCodeInputs.forEach((input) => {
    input.addEventListener("input", (e) => {
      e.target.value = e.target.value.toUpperCase().replace(/[^A-Z0-9]/g, "").slice(0, 8);
    });
  });

  // Copy invitation link helper
  const copyInviteBtns = document.querySelectorAll(".btn-copy-invite");
  copyInviteBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      const url = `${window.location.origin}/join-auction?code=${code}`;
      copyToClipboard(url, `Copied invitation link for room ${code}!`);
    });
  });

  // Copy room code helper
  const copyCodeBtns = document.querySelectorAll(".btn-copy-code");
  copyCodeBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const code = btn.getAttribute("data-code");
      copyToClipboard(code, `Copied room code: ${code}`);
    });
  });
});
