/**
 * RackTrack Professional Theme
 * Light mode only for a professional business appearance
 */

document.addEventListener('DOMContentLoaded', function() {
    // Remove any theme attribute to use the light theme consistently
    document.body.removeAttribute('data-theme');
    
    // Hide the theme toggle switches in the UI
    const themeToggles = document.querySelectorAll('.theme-switch-wrapper');
    themeToggles.forEach(toggle => {
        toggle.style.display = 'none';
    });
});