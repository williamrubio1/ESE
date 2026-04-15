// Variables globales
let selectedFile = null;
let processedFilename = null;
const modoProcesamiento = document.body.dataset.modo || 'carga';

// Elementos del DOM
const dropZone = document.getElementById('dropZone');
const fileInput = document.getElementById('fileInput');
const selectedFileDiv = document.getElementById('selectedFile');
const fileNameSpan = document.getElementById('fileName');
const removeFileBtn = document.getElementById('removeFile');
const processBtn = document.getElementById('processBtn');
const loader = document.getElementById('loader');
const statsSection = document.getElementById('statsSection');
const successNotification = document.getElementById('successNotification');
const errorNotification = document.getElementById('errorNotification');
const errorMessage = document.getElementById('errorMessage');
const downloadSection = document.getElementById('downloadSection');
const downloadBtn = document.getElementById('downloadBtn');
const loadLogsBtn = document.getElementById('loadLogsBtn');
const logsContent = document.getElementById('logsContent');

// Prevenir comportamiento por defecto del navegador para drag & drop
['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, preventDefaults, false);
    document.body.addEventListener(eventName, preventDefaults, false);
});

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

// Resaltar zona de drop cuando se arrastra un archivo
['dragenter', 'dragover'].forEach(eventName => {
    dropZone.addEventListener(eventName, highlight, false);
});

['dragleave', 'drop'].forEach(eventName => {
    dropZone.addEventListener(eventName, unhighlight, false);
});

function highlight(e) {
    dropZone.classList.add('drag-over');
}

function unhighlight(e) {
    dropZone.classList.remove('drag-over');
}

// Manejar archivos soltados
dropZone.addEventListener('drop', handleDrop, false);

function handleDrop(e) {
    const dt = e.dataTransfer;
    const files = dt.files;
    handleFiles(files);
}

// Manejar archivos seleccionados mediante el input
fileInput.addEventListener('change', function(e) {
    handleFiles(this.files);
});

// Procesar archivos seleccionados
function handleFiles(files) {
    if (files.length > 0) {
        const file = files[0];
        
        // Validar que sea un archivo JSON
        if (!file.name.endsWith('.json')) {
            showError('Por favor selecciona un archivo JSON válido');
            return;
        }
        
        selectedFile = file;
        fileNameSpan.textContent = file.name;
        selectedFileDiv.style.display = 'flex';
        dropZone.style.display = 'none';
        processBtn.disabled = false;
        
        // Ocultar secciones anteriores
        hideNotifications();
        statsSection.style.display = 'none';
        downloadSection.style.display = 'none';
    }
}

// Remover archivo seleccionado
removeFileBtn.addEventListener('click', function() {
    selectedFile = null;
    processedFilename = null;
    selectedFileDiv.style.display = 'none';
    dropZone.style.display = 'flex';
    processBtn.disabled = true;
    fileInput.value = '';
    
    // Ocultar secciones
    hideNotifications();
    statsSection.style.display = 'none';
    downloadSection.style.display = 'none';
    
    // Limpiar listas de detalles
    clearDetailLists();
});

// Procesar archivo
processBtn.addEventListener('click', async function() {
    if (!selectedFile) return;
    
    // Mostrar loader
    loader.style.display = 'block';
    processBtn.disabled = true;
    hideNotifications();
    statsSection.style.display = 'none';
    downloadSection.style.display = 'none';
    clearDetailLists();
    
    // Crear FormData
    const formData = new FormData();
    formData.append('archivo', selectedFile);
    
    try {
        const response = await fetch(`/procesar/${modoProcesamiento}`, {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (response.ok && data.success) {
            // Guardar nombre del archivo procesado
            processedFilename = data.filename;
            
            // Mostrar estadísticas
            displayStats(data.stats);
            
            // Mostrar notificación de éxito
            showSuccess();
            
            // Mostrar botón de descarga
            downloadSection.style.display = 'block';
        } else {
            showError(data.error || 'Error desconocido al procesar el archivo');
        }
    } catch (error) {
        showError('Error de conexión: ' + error.message);
    } finally {
        loader.style.display = 'none';
        processBtn.disabled = false;
    }
});

// Mostrar estadísticas
function displayStats(stats) {
    document.getElementById('statEncontrados').textContent = stats.medicamentos_encontrados || 0;
    document.getElementById('statUnidades').textContent = stats.unidades_sustituidas || 0;
    document.getElementById('statCodigos').textContent = stats.codigos_sustituidos || 0;
    document.getElementById('statNoEncontrados').textContent = stats.no_encontrados || 0;
    document.getElementById('statNuevos').textContent = stats.medicamentos_nuevos_en_cum || 0;
    document.getElementById('statProcedimientos').textContent = stats.procedimientos_modificados || 0;
    
    // Mostrar detalles de medicamentos no encontrados
    if (stats.no_encontrados_detalle && stats.no_encontrados_detalle.length > 0) {
        const detailsElem = document.getElementById('detailsNoEncontrados');
        const listElem = document.getElementById('listNoEncontrados');
        listElem.innerHTML = '';
        stats.no_encontrados_detalle.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${item.nombre}</strong> (Código: ${item.codigo || 'N/A'})`;
            listElem.appendChild(li);
        });
        detailsElem.style.display = 'block';
    }
    
    // Mostrar detalles de medicamentos nuevos en cum.json
    if (stats.medicamentos_nuevos_en_cum_detalle && stats.medicamentos_nuevos_en_cum_detalle.length > 0) {
        const detailsElem = document.getElementById('detailsNuevos');
        const listElem = document.getElementById('listNuevos');
        listElem.innerHTML = '';
        stats.medicamentos_nuevos_en_cum_detalle.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>${item.nombre}</strong> (Código: ${item.codigo || 'N/A'}, Unidad: ${item.unidad})`;
            listElem.appendChild(li);
        });
        detailsElem.style.display = 'block';
    }
    
    // Mostrar detalles de procedimientos modificados
    if (stats.procedimientos_modificados_detalle && stats.procedimientos_modificados_detalle.length > 0) {
        const detailsElem = document.getElementById('detailsProcedimientos');
        const listElem = document.getElementById('listProcedimientos');
        listElem.innerHTML = '';
        stats.procedimientos_modificados_detalle.forEach(item => {
            const li = document.createElement('li');
            li.innerHTML = `<strong>Código:</strong> ${item.codigo} | <strong>Dx:</strong> ${item.diagnostico} | Finalidad: ${item.finalidad_anterior} → ${item.finalidad_nueva}`;
            listElem.appendChild(li);
        });
        detailsElem.style.display = 'block';
    }
    
    statsSection.style.display = 'block';
    
    // Animación de los números
    animateStats();
}

// Animar contadores de estadísticas
function animateStats() {
    const statValues = document.querySelectorAll('.stat-value');
    statValues.forEach(stat => {
        const target = parseInt(stat.textContent);
        let current = 0;
        const increment = target / 20;
        const timer = setInterval(() => {
            current += increment;
            if (current >= target) {
                stat.textContent = target;
                clearInterval(timer);
            } else {
                stat.textContent = Math.floor(current);
            }
        }, 30);
    });
}

// Descargar archivo procesado
downloadBtn.addEventListener('click', function() {
    if (processedFilename) {
        window.location.href = `/descargar/${processedFilename}`;
    }
});

// Cargar logs
loadLogsBtn.addEventListener('click', async function() {
    try {
        const response = await fetch('/logs');
        const data = await response.json();
        
        if (data.logs && data.logs.length > 0) {
            logsContent.textContent = data.logs.join('');
            loadLogsBtn.style.display = 'none';
        } else {
            logsContent.textContent = 'No hay logs disponibles para el día de hoy.';
        }
    } catch (error) {
        logsContent.textContent = 'Error cargando los logs: ' + error.message;
    }
});

// Mostrar notificación de éxito
function showSuccess() {
    hideNotifications();
    successNotification.style.display = 'flex';
    setTimeout(() => {
        successNotification.style.display = 'none';
    }, 5000);
}

// Mostrar notificación de error
function showError(message) {
    hideNotifications();
    errorMessage.textContent = message;
    errorNotification.style.display = 'flex';
    setTimeout(() => {
        errorNotification.style.display = 'none';
    }, 5000);
}

// Ocultar todas las notificaciones
function hideNotifications() {
    successNotification.style.display = 'none';
    errorNotification.style.display = 'none';
}

// Limpiar listas de detalles
function clearDetailLists() {
    // Limpiar y ocultar lista de no encontrados
    document.getElementById('detailsNoEncontrados').style.display = 'none';
    document.getElementById('listNoEncontrados').innerHTML = '';
    
    // Limpiar y ocultar lista de nuevos en cum.json
    document.getElementById('detailsNuevos').style.display = 'none';
    document.getElementById('listNuevos').innerHTML = '';
    
    // Limpiar y ocultar lista de procedimientos modificados
    document.getElementById('detailsProcedimientos').style.display = 'none';
    document.getElementById('listProcedimientos').innerHTML = '';
}
