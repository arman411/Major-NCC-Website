import os
import re

templates_dir = r"e:\Major NCC Website\Major NCC Website\templates"

for filename in os.listdir(templates_dir):
    if filename.endswith('.html'):
        filepath = os.path.join(templates_dir, filename)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()

        # Replace css paths (match href="../css/xxx" or href="css/xxx")
        content = re.sub(r'href=[\"\'](\.\./)?css/(.*?)[\"\']', r'href="{{ url_for(\'static\', filename=\'css/\2\') }}"', content)
        
        # Replace js paths (match src="../js/xxx" or src="js/xxx")
        content = re.sub(r'src=[\"\'](\.\./)?js/(.*?)[\"\']', r'src="{{ url_for(\'static\', filename=\'js/\2\') }}"', content)
        
        # Replace image paths (match src="../images/xxx" or src="images/xxx")
        content = re.sub(r'src=[\"\'](\.\./)?images/(.*?)[\"\']', r'src="{{ url_for(\'static\', filename=\'images/\2\') }}"', content)
        
        # Replace page links (for Flask routes)
        pages = ['about', 'unit', 'activities', 'gallery', 'achievements', 'notices', 'contact', 'login', 'signup', 'enrollment', 'admin-dashboard']
        for page in pages:
            # Matches 'page.html' or '../page.html' or 'pages/page.html'
            # We map 'admin-dashboard' -> 'dashboard' route
            route_name = 'dashboard' if page == 'admin-dashboard' else page
            content = re.sub(fr'href=[\"\'](\.\./)?(pages/)?{page}\.html[\"\']', fr'href="{{{{ url_for(\'{route_name}\') }}}}"', content)
            
        # specifically fix index.html
        content = re.sub(r'href=[\"\'](\.\./)?index\.html[\"\']', r'href="{{ url_for(\'home\') }}"', content)

        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)

print("Updated HTML files for Jinja2 compatibility.")
