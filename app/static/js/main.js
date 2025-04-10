document.addEventListener('DOMContentLoaded', () => {
    // Инициализация вкладок Bootstrap через API
    const triggerTabList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tab"]'));
    triggerTabList.forEach(function(triggerEl) {
        const tabTrigger = new bootstrap.Tab(triggerEl);
        
        triggerEl.addEventListener('click', function(event) {
            event.preventDefault();
            tabTrigger.show();
        });
    });

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
    
    // Элементы интерфейса прайс-листа
    const priceListForm = document.getElementById('price-list-form');
    const priceListFileInput = document.getElementById('price-list-file');
    const supplierIdInput = document.getElementById('supplier-id');
    const replaceExistingCheckbox = document.getElementById('replace-existing');
    const clearBySupplierCheckbox = document.getElementById('clear-by-supplier');
    const priceListUploadBtn = document.getElementById('price-list-upload-btn');
    const priceListLoading = document.getElementById('price-list-loading');
    const priceListProgressBar = document.getElementById('price-list-progress-bar');
    const priceListResultsCard = document.getElementById('price-list-results-card');
    const priceListSuccessMessage = document.getElementById('price-list-success-message');
    const priceListNewBtn = document.getElementById('price-list-new-btn');
    const priceListErrorCard = document.getElementById('price-list-error-card');
    const priceListErrorMessage = document.getElementById('price-list-error-message');
    const priceListTryAgainBtn = document.getElementById('price-list-try-again-btn');
    
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
    let currentPriceListId = null;

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
            // Добавляем ID прогресс-бара в запрос
            const progressBarId = document.getElementById('progress-bar').getAttribute('data-progress-id');
            if (progressBarId) {
                formData.append('progress_bar_id', progressBarId);
            }
            // Используем единый URL для всех типов файлов
            const uploadUrl = '/api/documents/upload';
            console.log(`Sending file to ${uploadUrl}, type: ${fileExt}`);

            // Останавливаем текущий мониторинг прогресса, если есть
            // stopProgressMonitoring();
            // Запускаем мониторинг прогресса
            const fileType = fileExt === 'xlsx' ? 'xlsx' : 'ocr';
            startProgressMonitoring(progressBarId, fileType);
            const response = await fetch(uploadUrl, {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || `Произошла ошибка при загрузке ${uploadType === 'document' ? 'документа' : 'изображения'}`);
            }

            const data = await response.json();
            console.log('Received data:', data);
            
            // Сохраняем ID документа для экспорта
            currentDocumentId = data.id;
            currentFilename = data.original_filename;
            
            
            
            // Ждем завершения обработки
            while (true) {
                await new Promise(resolve => setTimeout(resolve, 2000));
                
                try {
                    const statusResponse = await fetch(`/api/documents/${data.id}`);
                    if (!statusResponse.ok) {
                        throw new Error('Не удалось получить статус обработки');
                    }
                    
                    const statusData = await statusResponse.json();
                    if (statusData.status === 'completed') {
                        // Обработка завершена
                        stopProgressMonitoring();
                        // Отображаем результаты
                        displayResults(statusData);
                        break;
                    } else if (statusData.status === 'error') {
                        // Произошла ошибка
                        stopProgressMonitoring();
                        throw new Error(statusData.error || 'Произошла ошибка при обработке документа');
                    }
                    // Иначе продолжаем ожидание
                } catch (statusError) {
                    console.error('Ошибка при проверке статуса:', statusError);
                    // Продолжаем ожидание даже при ошибках запроса статуса
                }
            }
        } catch (error) {
            console.error('Error uploading file:', error);
            showError(error.message);
            // Останавливаем мониторинг прогресса при ошибке
            stopProgressMonitoring();
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

    // Обработчик отправки формы загрузки прайс-листа
    if (priceListForm) {
        priceListForm.addEventListener('submit', async (e) => {
            e.preventDefault();

            const file = priceListFileInput.files[0];
            if (!file) {
                showPriceListError('Пожалуйста, выберите файл прайс-листа для загрузки');
                return;
            }

            // Скрываем предыдущие результаты и ошибки
            priceListResultsCard.classList.add('d-none');
            priceListErrorCard.classList.add('d-none');

            // Показываем загрузчик
            priceListLoading.classList.remove('d-none');
            priceListProgressBar.style.width = '0%';
            let uploadId = null;

            // Начальный текст загрузки
            const priceListLoadingText = document.getElementById('price-list-loading-text');
            priceListLoadingText.textContent = `Загрузка прайс-листа "${file.name}"...`;

            // Функция для получения статуса загрузки
            async function checkUploadStatus() {
                if (!uploadId) return;
                
                try {
                    const response = await fetch(`/api/price-lists/${uploadId}/status`);
                    if (response.ok) {
                        const statusData = await response.json();
                        if (statusData.status === 'processing') {
                            const percentComplete = statusData.percent_complete || 0;
                            priceListProgressBar.style.width = `${percentComplete}%`;
                            
                            // Обновляем текст с информацией о прогрессе
                            if (statusData.processed_items && statusData.total_items) {
                                // Добавляем счетчик внутрь прогрессбара
                                priceListProgressBar.innerHTML = `${statusData.processed_items} / ${statusData.total_items}`;
                                
                                // Обновляем текст под прогрессбаром
                                priceListLoadingText.textContent = `Обработано ${statusData.processed_items} из ${statusData.total_items} товаров`;
                                
                                if (statusData.current_stage) {
                                    priceListLoadingText.textContent += ` (${statusData.current_stage})`;
                                }
                            }
                        }
                    }
                } catch (error) {
                    console.warn('Ошибка при получении статуса загрузки:', error);
                }
            }

            let statusInterval = null;

            try {
                // Получаем значения параметров
                const supplierId = supplierIdInput.value.trim();
                const replaceExisting = replaceExistingCheckbox.checked;
                const clearBySupplier = clearBySupplierCheckbox.checked;

                // Отправляем файл на сервер
                const formData = new FormData();
                formData.append('file', file);
                
                // Добавляем параметры
                if (supplierId) {
                    formData.append('supplier_id', supplierId);
                }
                formData.append('replace_existing', replaceExisting);
                formData.append('clear_by_supplier', clearBySupplier);

                // URL для загрузки прайс-листа
                const uploadUrl = '/api/price-lists/upload';
                console.log(`Отправка прайс-листа на ${uploadUrl}`);
                
                // Запускаем симуляцию прогресса для начального этапа загрузки
                let progress = 0;
                const progressInterval = setInterval(() => {
                    progress += Math.random() * 5;
                    if (progress > 30) progress = 30; // Ограничиваем до 30% до получения реальных данных
                    priceListProgressBar.style.width = `${progress}%`;
                }, 500);
                
                const response = await fetch(uploadUrl, {
                    method: 'POST',
                    body: formData
                });

                // Останавливаем симуляцию начального прогресса
                clearInterval(progressInterval);

                if (!response.ok) {
                    const errorData = await response.json();
                    throw new Error(errorData.detail || 'Произошла ошибка при загрузке прайс-листа');
                }

                const data = await response.json();
                console.log('Получены данные:', data);
                
                // Сохраняем ID прайс-листа
                currentPriceListId = data.id;
                uploadId = data.id;
                
                if (data.status === 'processing') {
                    // Запускаем интервал проверки статуса
                    statusInterval = setInterval(checkUploadStatus, 2000);
                    priceListLoadingText.textContent = 'Прайс-лист загружен, идет обработка товаров...';
                    priceListProgressBar.style.width = '30%';
                    
                    // Ждем завершения обработки
                    while (true) {
                        await new Promise(resolve => setTimeout(resolve, 3000));
                        const statusResponse = await fetch(`/api/price-lists/${uploadId}/status`);
                        const statusData = await statusResponse.json();
                        
                        if (statusData.status === 'completed') {
                            // Обработка завершена
                            clearInterval(statusInterval);
                            priceListProgressBar.style.width = '100%';
                            priceListProgressBar.innerHTML = `${statusData.total_items} / ${statusData.total_items}`;
                            
                            // Отображаем результаты
                            displayPriceListResults(statusData.result);
                            break;
                        } else if (statusData.status === 'error') {
                            // Произошла ошибка
                            clearInterval(statusInterval);
                            throw new Error(statusData.error || 'Произошла ошибка при обработке прайс-листа');
                        }
                    }
                } else {
                    // Обработка завершена сразу
                    priceListProgressBar.style.width = '100%';
                    priceListProgressBar.innerHTML = data.total_items ? `${data.total_items} / ${data.total_items}` : 'Завершено';
                    
                    // Отображаем результаты
                    displayPriceListResults(data);
                }
            } catch (error) {
                console.error('Ошибка загрузки прайс-листа:', error);
                showPriceListError(error.message);
                if (statusInterval) {
                    clearInterval(statusInterval);
                }
            } finally {
                // Скрываем загрузчик в любом случае
                setTimeout(() => {
                    priceListLoading.classList.add('d-none');
                }, 500);
            }
        });
    }

    // Обработчик кнопки "Загрузить другой прайс-лист"
    if (priceListNewBtn) {
        priceListNewBtn.addEventListener('click', () => {
            priceListResultsCard.classList.add('d-none');
            priceListFileInput.value = '';
            supplierIdInput.value = '';
            replaceExistingCheckbox.checked = false;
            clearBySupplierCheckbox.checked = false;
        });
    }

    // Обработчик кнопки "Попробовать снова" после ошибки прайс-листа
    if (priceListTryAgainBtn) {
        priceListTryAgainBtn.addEventListener('click', () => {
            priceListErrorCard.classList.add('d-none');
        });
    }

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
                    <td>${itemData.Количество || itemData['Кол-во'] || '-'}</td>
                    <td>${itemData['Ед.изм.'] || itemData['Ед. изм.'] || '-'}</td>
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
                    <td>${itemData['Кол-во'] || '-'}</td>
                    <td>${itemData['Ед. изм.'] || '-'}</td>
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

    // Функция отображения результатов загрузки прайс-листа
    function displayPriceListResults(data) {
        // Отображаем карточку результатов
        priceListResultsCard.classList.remove('d-none');
        
        // Заполняем сообщение об успехе
        const itemsText = `${data.total_items} товаров`;
        const categoryText = `${data.categories_count} категорий`;
        const supplierText = data.supplier_id ? `поставщика ${data.supplier_id}` : '';
        
        priceListSuccessMessage.textContent = `Прайс-лист "${data.filename}" успешно загружен. 
            Добавлено ${itemsText} из ${categoryText} ${supplierText}. 
            Дата прайс-листа: ${data.date}, валюта: ${data.currency}.`;
    }

    // Функция отображения ошибки загрузки прайс-листа
    function showPriceListError(message) {
        priceListErrorCard.classList.remove('d-none');
        priceListErrorMessage.textContent = message;
    }

    // Функция отображения ошибки
    function showError(message) {
        errorMessage.textContent = message;
        errorCard.classList.remove('d-none');
    }
}); 