// подписка
function submitFriendForm(event) {
                            event.preventDefault();

                            const form = document.getElementById('friendRequestForm');
                            const formData = new FormData(form);

                            fetch(form.action, {
                                method: form.method,
                                body: formData
                            })
                                .then(response => response.json())
                                .then(data => {
                                    if (data.status_sub === true) {
                                        alert("Вы подписались на пользователя " + profileUserName);
                                    } else if (data.status_sub === false) {
                                        alert("Вы отписались от пользователя " + profileUserName);
                                    } else {
                                        alert("Неизвестный ответ сервера");
                                    }
                                })
                                .catch(error => {
                                    console.error("Ошибка:", error);
                                    alert("Произошла ошибка при отправке запроса");
                                });
                        }

// лайк
document.addEventListener("DOMContentLoaded", function () {
    document.addEventListener("click", async function (e) {

        const button = e.target.closest(".like-button");
        if (!button) return;

        e.preventDefault(); 

        const formId = button.dataset.formId;
        const form = document.getElementById(formId);
        const formData = new FormData(form);

        try {
            const response = await fetch("/profile/like-post", {
                method: "POST",
                body: formData
            });

            if (!response.ok) throw new Error("Ошибка при отправке");

            const result = await response.json();

            const likeSpan = button.querySelector("span");
            const countSpan = button.querySelector(".number");

            countSpan.textContent = result.likes;

            if (result.liked) {
                likeSpan.style.color = "#3644D9";
                countSpan.style.color = "#3644D9";
            } else {
                likeSpan.style.color = "";
                countSpan.style.color = "";
            }

        } catch (err) {
            console.error("Ошибка лайка:", err);
        }
    });
});
