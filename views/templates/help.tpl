<!DOCTYPE html>
<html>
<head>
    <title>HWatch - Documentation & Configuration Guide</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/svg+xml" href="/static/img/hwatch.svg">
    <style>
        body {
            font-family: "CeraRoundPro-Regular", BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f8f9fa;
            margin: 0;
            padding: 0;
        }
        
        .help-container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            min-height: 100vh;
            box-shadow: 0 0 20px rgba(0,0,0,0.1);
        }
        
        .help-header {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 30px;
            text-align: center;
            border-bottom: 4px solid #0056b3;
        }
        
        .help-header h1 {
            margin: 0;
            font-size: 2.5rem;
            font-weight: 300;
        }
        
        .help-header p {
            font-size: 1.1rem;
            margin: 5px 0;
            opacity: 0.9;
        }
        
        .help-content {
            padding: 40px;
        }
        
        .markdown-content {
            max-width: none;
        }
        
        .markdown-content h1, 
        .markdown-content h2, 
        .markdown-content h3 {
            color: #212529;
            margin-top: 5px;
            margin-bottom: 1rem;
        }
        
        .markdown-content h1 {
            font-size: 2rem;
            border-bottom: 3px solid #007bff;
            padding-bottom: 10px;
        }
        
        .markdown-content h2 {
            font-size: 1.5rem;
            border-bottom: 2px solid #6c757d;
            padding-bottom: 4px;
        }
        
        .markdown-content h3 {
            font-size: 1.25rem;
            color: #495057;
        }
        
        .markdown-content code {
            background: #f8f9fa;
            padding: 2px 6px;
            border-radius: 4px;
            font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 0.9em;
            color: #e83e8c;
        }
        
        .markdown-content pre {
            background: #f8f9fa;
            border: 1px solid #e9ecef;
            border-radius: 6px;
            padding: 20px;
            overflow-x: auto;
            margin: 20px 0;
        }
        
        .markdown-content pre code {
            background: none;
            padding: 0;
            color: #495057;
            font-size: 0.875rem;
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .markdown-content th,
        .markdown-content td {
            border: 1px solid #dee2e6;
            padding: 12px 15px;
            text-align: left;
        }
        
        .markdown-content th {
            background: #e9ecef;
            font-weight: 600;
            color: #495057;
        }
        
        .markdown-content tr:nth-child(even) {
            background: #f8f9fa;
        }
        
        .markdown-content blockquote {
            border-left: 4px solid #007bff;
            margin: 20px 0;
            padding: 10px 20px;
            background: #f8f9fa;
            font-style: italic;
        }
        
        .markdown-content ul, 
        .markdown-content ol {
            padding-left: 30px;
            margin: 15px 0;
        }
        
        .markdown-content li {
            margin: 8px 0;
        }
        
        .close-button {
            position: fixed;
            top: 20px;
            right: 20px;
            background: #dc3545;
            color: white;
            border: none;
            border-radius: 50%;
            width: 50px;
            height: 50px;
            font-size: 20px;
            cursor: pointer;
            box-shadow: 0 4px 8px rgba(0,0,0,0.3);
            transition: all 0.2s;
            z-index: 1000;
        }
        
        .close-button:hover {
            background: #c82333;
            transform: scale(1.1);
        }
        
        .config-highlight {
            background: linear-gradient(135deg,rgb(247, 247, 247));
            border: 2px solidrgb(135, 142, 149);
            border-radius: 4px;
            padding: 5px;
            margin: 10px 0;
        }
        
        .config-highlight h3 {
            color:rgb(178, 185, 192);
            margin-top: 0;
        }
        
        @media (max-width: 768px) {
            .help-content {
                padding: 20px;
            }
            
            .help-header {
                padding: 20px;
            }
            
            .help-header h1 {
                font-size: 2rem;
            }
        }
    </style>
</head>
<body>
    <div class="help-container">
        <button class="close-button" onclick="window.close()" title="Close Help">&times;</button>
        
        <div class="help-header">
            <h1>🚀 HWatch Documentation</h1>
            <p>Network Device Monitoring System - Configuration Guide & Documentation</p>
        </div>
        
        <div class="help-content">
            <div class="markdown-content">
                {{ readme_content | safe }}
            </div>
        </div>
    </div>
    
    <script>
        // Add special styling to configuration sections
        document.querySelectorAll('h2, h3').forEach(heading => {
            if (heading.textContent.toLowerCase().includes('config') || 
                heading.textContent.toLowerCase().includes('配置')) {
                const section = document.createElement('div');
                section.className = 'config-highlight';
                heading.parentNode.insertBefore(section, heading);
                section.appendChild(heading);
                
                // Move the next few elements into the highlight section
                let nextElement = section.nextElementSibling;
                while (nextElement && !nextElement.matches('h1, h2')) {
                    const elementToMove = nextElement;
                    nextElement = nextElement.nextElementSibling;
                    if (elementToMove.matches('h3') && section.children.length > 1) {
                        // Stop if we hit another h3 (unless it's the first one)
                        break;
                    }
                    section.appendChild(elementToMove);
                }
            }
        });
        
        // Handle close button and keyboard shortcut
        document.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                window.close();
            }
        });
    </script>
</body>
</html>