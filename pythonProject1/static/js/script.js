// Select the analysis box
const analysisBox = document.querySelector('.analysis-content');

if (analysisBox) {
    analysisBox.addEventListener('click', function() {
        // Toggle the 'expanded' class on/off
        this.classList.toggle('expanded');
    });
}