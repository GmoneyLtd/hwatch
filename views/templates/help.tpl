<!DOCTYPE html>
<html>
<head>
    <title>HWatch - Documentation & Configuration Guide</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/svg+xml" href="/static/img/hwatch.svg">
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10.6.1/dist/mermaid.min.js"></script>
    <style>
        body {
            font-family: "CeraRoundPro-Regular", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            line-height: 1.4;
            color: #000;
            background: #fff;
            margin: 0;
            padding: 0;
            font-size: 12px;
        }
        
        .help-container {
            max-width: 900px;
            margin: 0 auto;
            background: #fff;
            min-height: 100vh;
        }
        
        .help-header {
            background: #00000061;
            color: #fff;
            padding: 10px;
            text-align: center;
            border-bottom: 1px solid #000;
        }
        
        .help-header h1 {
            margin: 0;
            font-size: 1.3rem;
            font-weight: 400;
        }
        
        .help-header p {
            margin: 5px 0 0 0;
            font-size: 0.8rem;
            opacity: 0.9;
        }
        
        .help-content {
            padding: 15px;
        }
        
        .markdown-content {
            max-width: none;
        }
        
        .markdown-content h1, 
        .markdown-content h2, 
        .markdown-content h3 {
            color: #000;
            margin-top: 1rem;
            margin-bottom: 0.5rem;
        }
        
        .markdown-content h1 {
            font-size: 1.1rem;
            border-bottom: 1px solid #000;
            padding-bottom: 3px;
        }
        
        .markdown-content h2 {
            font-size: 1rem;
            border-bottom: 1px solid #ccc;
            padding-bottom: 2px;
        }
        
        .markdown-content h3 {
            font-size: 0.9rem;
            color: #333;
        }
        
        .markdown-content p {
            font-size: 12px;
            margin: 0.5rem 0;
        }
        
        .markdown-content code {
            background: #f0f0f0;
            padding: 2px 3px;
            border-radius: 2px;
            font-family: 'Monaco', 'Consolas', 'Courier New', monospace;
            font-size: 10px;
            color: #000;
            border: 1px solid #ccc;
        }
        
        .markdown-content pre {
            background: #f5f5f5;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 8px;
            overflow-x: auto;
            margin: 8px 0;
        }
        
        .markdown-content pre code {
            background: none;
            padding: 0;
            color: #000;
            font-size: 10px;
            border: none;
        }
        
        .markdown-content table {
            width: 100%;
            border-collapse: collapse;
            margin: 8px 0;
            background: #fff;
            border: 1px solid #ccc;
            font-size: 11px;
        }
        
        .markdown-content th,
        .markdown-content td {
            border: 1px solid #ccc;
            padding: 4px 6px;
            text-align: left;
        }
        
        .markdown-content th {
            background: #f0f0f0;
            font-weight: 600;
            color: #000;
        }
        
        .markdown-content tr:nth-child(even) {
            background: #f8f8f8;
        }
        
        .markdown-content blockquote {
            border-left: 2px solid #000;
            margin: 8px 0;
            padding: 5px 10px;
            background: #f5f5f5;
            font-style: italic;
            font-size: 11px;
        }
        
        .markdown-content ul, 
        .markdown-content ol {
            padding-left: 18px;
            margin: 6px 0;
            font-size: 12px;
        }
        
        .markdown-content li {
            margin: 2px 0;
        }
        
        .close-button {
            position: fixed;
            top: 10px;
            right: 10px;
            background: #000;
            color: #fff;
            border: none;
            border-radius: 50%;
            width: 26px;
            height: 26px;
            font-size: 12px;
            cursor: pointer;
            transition: all 0.2s;
            z-index: 1000;
        }
        
        .close-button:hover {
            background: #333;
            transform: scale(1.1);
        }
        
        .config-highlight {
            background: #f5f5f5;
            border: 1px solid #000;
            border-radius: 3px;
            padding: 8px;
            margin: 8px 0;
        }
        
        .config-highlight h3 {
            color: #000;
            margin-top: 0;
            font-size: 0.9rem;
        }
        
        /* Mermaid diagram styles */
        .mermaid {
            background: #fff;
            border: 1px solid #ccc;
            border-radius: 3px;
            padding: 10px;
            margin: 10px 0;
            text-align: center;
        }
        
        .mermaid svg {
            max-width: 100%;
            height: auto;
        }
        
        @media (max-width: 768px) {
            .help-content {
                padding: 10px;
            }
            
            .help-header {
                padding: 10px;
            }
            
            .help-header h1 {
                font-size: 1.1rem;
            }
            
            .markdown-content h1 {
                font-size: 1rem;
            }
            
            .markdown-content h2 {
                font-size: 0.9rem;
            }
            
            .markdown-content h3 {
                font-size: 0.8rem;
            }
            
            .markdown-content p {
                font-size: 11px;
            }
        }
    </style>
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
        // Initialize Mermaid
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            themeVariables: {
                primaryColor: '#fff',
                primaryTextColor: '#000',
                primaryBorderColor: '#000',
                lineColor: '#000',
                secondaryColor: '#f0f0f0',
                tertiaryColor: '#f5f5f5'
            }
        });
        
        // Add special styling to configuration sections
        document.addEventListener('DOMContentLoaded', function() {
            // Convert mermaid code blocks to mermaid divs
            document.querySelectorAll('pre code').forEach(function(codeBlock) {
                if (codeBlock.textContent.trim().startsWith('graph ') || 
                    codeBlock.textContent.trim().startsWith('flowchart ')) {
                    const mermaidDiv = document.createElement('div');
                    mermaidDiv.className = 'mermaid';
                    mermaidDiv.textContent = codeBlock.textContent;
                    codeBlock.parentElement.parentElement.replaceChild(mermaidDiv, codeBlock.parentElement);
                }
            });
            
            // Re-initialize mermaid after DOM changes
            mermaid.init();
            
            // Add configuration highlights
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