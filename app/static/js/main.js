document.addEventListener('DOMContentLoaded', () => {
    // Элементы интерфейса
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('document-file');
    const uploadTypeSelect = document.getElementById('upload-type');
    const uploadButton = document.getElementById('upload-btn');
    const fileInfo = document.getElementById('file-info');
    const infoFilename = document.getElementById('info-filename');
    const infoFiletype = document.getElementById('info-filetype');
    const infoFilesize = document.getElementById('info-filesize');
    const loadingSection = document.getElementById('loading');
    const loadingText = document.getElementById('loading-text');
    const progressBar = document.getElementById('progress-bar');
    const resultsCard = document.getElementById('results-card');
    const resultFilename = document.getElementById('result-filename');
    const resultsTableBody = document.getElementById('results-table-body');
    const exportButton = document.getElementById('export-btn');
    const retryButton = document.getElementById('retry-btn');
    const errorCard = document.getElementById('error-card');
    const errorMessage = document.getElementById('error-message');
    const tryAgainButton = document.getElementById('try-again-btn');
    
    // Элементы интерфейса чата
    const chatForm = document.getElementById('chat-form');
    const chatMessageInput = document.getElementById('chat-message');
    const chatMessages = document.getElementById('chat-messages');
    const chatResultsCard = document.getElementById('chat-results-card');
    const chatResultsTableBody = document.getElementById('chat-results-table-body');
    const chatExportButton = document.getElementById('chat-export-btn');

    // Переменные для хранения текущего документа/сообщения
    let currentDocumentId = null;
    let currentFilename = null;
    let currentChatMessageId = null;

    // Расширения для изображений
    const imageExtensions = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'tiff', 'svg'];
    
    // Функция форматирования размера файла
    const formatFileSize = (bytes) => {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    };

    // Обработчик изменения файла
    fileInput.addEventListener('change', (e) => {
        const file = e.target.files[0];
        if (!file) {
            fileInfo.classList.add('d-none');
            return;
        }

        // Отображаем информацию о файле
        infoFilename.textContent = file.name;
        infoFiletype.textContent = file.type || 'Неизвестный тип';
        infoFilesize.textContent = formatFileSize(file.size);
        fileInfo.classList.remove('d-none');

        // Автоматическое переключение типа загрузки на основе расширения
        const fileExt = file.name.split('.').pop().toLowerCase();
        if (imageExtensions.includes(fileExt)) {
            uploadTypeSelect.value = 'image';
        } else {
            uploadTypeSelect.value = 'document';
        }
    });

    // Обработчик отправки формы загрузки файла
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const file = fileInput.files[0];
        if (!file) {
            showError('Пожалуйста, выберите файл для загрузки');
            return;
        }

        // Скрываем предыдущие результаты и ошибки
        resultsCard.classList.add('d-none');
        errorCard.classList.add('d-none');

        // Показываем загрузчик
        loadingSection.classList.remove('d-none');
        progressBar.style.width = '0%';

        // Тип загрузки и расширение файла
        const uploadType = uploadTypeSelect.value;
        const fileExt = file.name.split('.').pop().toLowerCase();

        // Анимация прогресса (симуляция)
        let progress = 0;
        const progressInterval = setInterval(() => {
            progress += Math.random() * 10;
            if (progress > 90) progress = 90;
            progressBar.style.width = `${progress}%`;
        }, 300);

        try {
            // Отправляем файл на сервер
            const formData = new FormData();
            formData.append('file', file);
            
            // Добавляем тип файла в запрос, чтобы сервер мог корректно определить
            if (imageExtensions.includes(fileExt)) {
                formData.append('file_type', 'image');
            } else {
                formData.append('file_type', fileExt);
            }

            // Используем единый URL для всех типов файлов
            const uploadUrl = '/api/documents/upload';
            console.log(`Sending file to ${uploadUrl}, type: ${fileExt}`);
            
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });

            // Останавливаем анимацию прогресса
            clearInterval(progressInterval);
            progressBar.style.width = '100%';

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Произошла ошибка при загрузке ${uploadType === 'document' ? 'документа' : 'изображения'}`);
            }

            const data = await response.json();
            console.log('Received data:', data);
            
            // Сохраняем ID документа для экспорта
            currentDocumentId = data.id;
            currentFilename = data.original_filename;
            
            // Отображаем результаты
            displayResults(data);
        } catch (error) {
            console.error('Error uploading file:', error);
            showError(error.message);
        } finally {
            // Скрываем загрузчик в любом случае
            setTimeout(() => {
                loadingSection.classList.add('d-none');
            }, 500);
        }
    });

    // Обработчик отправки формы чата
    chatForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const messageText = chatMessageInput.value.trim();
        if (!messageText) {
            return;
        }

        // Добавляем сообщение пользователя в чат
        addChatMessage(messageText, 'user');
        
        // Очищаем поле ввода
        chatMessageInput.value = '';

        // Добавляем индикатор загрузки
        const loadingMessageId = addChatMessage('Обрабатываю ваше сообщение...', 'system');
        
        try {
            // Отправляем текстовое сообщение на сервер
            const response = await fetch('/api/chat/message', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ text: messageText })
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Произошла ошибка при обработке сообщения');
            }

            const data = await response.json();
            console.log('Received chat data:', data);
            
            // Удаляем индикатор загрузки
            removeChatMessage(loadingMessageId);
            
            // Сохраняем ID сообщения для экспорта
            currentChatMessageId = data.id;
            
            // Добавляем ответ системы в чат
            addChatMessage('Сообщение обработано. Результаты отображены ниже.', 'system');
            
            // Отображаем результаты
            displayChatResults(data);
        } catch (error) {
            console.error('Error processing chat message:', error);
            
            // Обновляем индикатор загрузки на сообщение об ошибке
            document.getElementById(loadingMessageId).textContent = 'Ошибка: ' + error.message;
        }
    });

    // Функция для добавления сообщения в чат
    function addChatMessage(message, type) {
        const messageId = 'msg-' + Date.now();
        const messageElement = document.createElement('div');
        messageElement.id = messageId;
        messageElement.className = `message ${type}-message`;
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        
        // Прокручиваем чат вниз
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        return messageId;
    }

    // Функция для удаления сообщения из чата
    function removeChatMessage(messageId) {
        const messageElement = document.getElementById(messageId);
        if (messageElement) {
            messageElement.remove();
        }
    }

    // Функция отображения результатов из файла
    function displayResults(data) {
        // Очищаем предыдущие результаты
        resultsTableBody.innerHTML = '';
        
        // Отображаем имя файла
        resultFilename.textContent = data.original_filename;
        
        // Добавляем элементы в таблицу
        data.items.forEach(item => {
            try {
                // Парсим JSON-строку текста элемента
                const itemData = JSON.parse(item.text);
                
                // Создаем новую строку таблицы
                const row = document.createElement('tr');
                
                // Добавляем ячейки
                row.innerHTML = `
                    <td>${itemData.Наименование || '-'}</td>
                    <td>${itemData.Количество || '-'}</td>
                    <td>${itemData['Ед.изм.'] || '-'}</td>
                `;
                
                // Добавляем строку в таблицу
                resultsTableBody.appendChild(row);
            } catch (e) {
                console.warn('Could not parse item:', item.text, e);
            }
        });
        
        // Если нет результатов, добавляем пустую строку
        if (data.items.length === 0) {
            resultsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">Нет результатов</td></tr>';
        }
        
        // Показываем карточку с результатами
        resultsCard.classList.remove('d-none');
    }

    // Функция отображения результатов из чата
    function displayChatResults(data) {
        // Очищаем предыдущие результаты
        chatResultsTableBody.innerHTML = '';
        
        // Добавляем элементы в таблицу
        data.items.forEach(item => {
            try {
                // Парсим JSON-строку текста элемента
                const itemData = JSON.parse(item.text);
                
                // Создаем новую строку таблицы
                const row = document.createElement('tr');
                
                // Добавляем ячейки
                row.innerHTML = `
                    <td>${itemData.Наименование || '-'}</td>
                    <td>${itemData.Количество || '-'}</td>
                    <td>${itemData['Ед.изм.'] || '-'}</td>
                `;
                
                // Добавляем строку в таблицу
                chatResultsTableBody.appendChild(row);
            } catch (e) {
                console.warn('Could not parse item:', item.text, e);
            }
        });
        
        // Если нет результатов, добавляем пустую строку
        if (data.items.length === 0) {
            chatResultsTableBody.innerHTML = '<tr><td colspan="3" class="text-center">Нет результатов</td></tr>';
        }
        
        // Показываем карточку с результатами
        chatResultsCard.classList.remove('d-none');
    }

    // Обработчик кнопки экспорта
    exportButton.addEventListener('click', async () => {
        if (!currentDocumentId) {
            showError('Документ не загружен или не обработан');
            return;
        }
        
        try {
            const response = await fetch(`/api/documents/${currentDocumentId}/export`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Произошла ошибка при экспорте');
            }
            
            const data = await response.json();
            console.log('Export data:', data);
            
            // Скачиваем файл
            window.location.href = data.download_url;
        } catch (error) {
            console.error('Error exporting file:', error);
            showError(error.message);
        }
    });

    // Обработчик кнопки экспорта чата
    chatExportButton.addEventListener('click', async () => {
        if (!currentChatMessageId) {
            addChatMessage('Ошибка: Сообщение не обработано', 'system');
            return;
        }
        
        try {
            const response = await fetch(`/api/chat/messages/${currentChatMessageId}/export`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Произошла ошибка при экспорте');
            }
            
            const data = await response.json();
            console.log('Export chat data:', data);
            
            // Добавляем сообщение об успешном экспорте
            addChatMessage('Результаты успешно экспортированы', 'system');
            
            // Скачиваем файл
            window.location.href = data.download_url;
        } catch (error) {
            console.error('Error exporting chat results:', error);
            addChatMessage('Ошибка: ' + error.message, 'system');
        }
    });

    // Обработчик кнопки "Загрузить другой файл"
    retryButton.addEventListener('click', () => {
        // Сбрасываем форму
        uploadForm.reset();
        fileInfo.classList.add('d-none');
        
        // Скрываем результаты и ошибки
        resultsCard.classList.add('d-none');
        errorCard.classList.add('d-none');
        
        // Сбрасываем текущий документ
        currentDocumentId = null;
        currentFilename = null;
    });

    // Обработчик кнопки "Попробовать снова"
    tryAgainButton.addEventListener('click', () => {
        // Сбрасываем форму
        uploadForm.reset();
        fileInfo.classList.add('d-none');
        
        // Скрываем ошибку
        errorCard.classList.add('d-none');
    });

    // Функция отображения ошибки
    function showError(message) {
        errorMessage.textContent = message;
        errorCard.classList.remove('d-none');
    }
}); 