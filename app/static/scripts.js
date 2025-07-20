document.addEventListener('DOMContentLoaded', function() {
    const sections = document.querySelectorAll('.section');

    const observerOptions = {
        root: null, // Dùng viewport làm root
        rootMargin: '0px', // Không có margin thêm
        threshold: 0.1 // Kích hoạt khi 10% của phần tử hiển thị trong viewport
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            const contentElement = entry.target.querySelector('.content'); // Lấy phần tử .content bên trong section

            if (contentElement) { // Đảm bảo phần tử .content tồn tại
                if (entry.isIntersecting) {
                    // Khi phần tử đi vào viewport
                    contentElement.classList.add('active');

                    // Nếu có các phần tử con có hiệu ứng riêng (như q-type), đảm bảo chúng cũng được kích hoạt
                    const qTypes = contentElement.querySelectorAll('.q-type');
                    qTypes.forEach(qType => {
                        qType.classList.add('active'); // Kích hoạt hiệu ứng cho từng q-type
                    });

                } else {
                    // Khi phần tử rời khỏi viewport
                    contentElement.classList.remove('active');

                    // Loại bỏ class active khỏi các phần tử con để reset hiệu ứng
                    const qTypes = contentElement.querySelectorAll('.q-type');
                    qTypes.forEach(qType => {
                        qType.classList.remove('active');
                    });
                }
            }
        });
    }, observerOptions);

    sections.forEach(section => {
        observer.observe(section);
    });
});