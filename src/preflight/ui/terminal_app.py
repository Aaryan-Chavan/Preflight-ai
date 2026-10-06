import os
import tempfile
import webview
import markdown
from preflight.core.models import Report, Decision

def show_review_ui(report: Report) -> Decision:
    """
    Displays a modern, Tailwind-styled webview popup for the developer to review the AI risk assessment.
    """
    decision = Decision.CANCEL  # Default failsafe

    # 1. Prepare the data
    risk_val = getattr(report.popup.risk_level, "value", str(report.popup.risk_level)).upper()
    conf_val = report.popup.confidence_percentage
    branch_val = report.popup.branch
    time_val = report.meta.analysis_ms

    # Convert Markdown summary to HTML
    raw_summary = report.detailed_markdown or report.popup.ai_recommendation or "No detailed summary available."
    html_summary = markdown.markdown(raw_summary)

    risk_color_class = "text-emerald-400" if "LOW" in risk_val else "text-red-400" if "HIGH" in risk_val else "text-amber-400"
    indicator_bg = "bg-emerald-500" if "LOW" in risk_val else "bg-red-500" if "HIGH" in risk_val else "bg-amber-500"

    # 2. Build the HTML UI using Tailwind CSS via CDN
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en" class="dark">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Preflight AI Review</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <style>
            /* Custom scrollbar for the dark theme */
            ::-webkit-scrollbar {{ width: 8px; }}
            ::-webkit-scrollbar-track {{ background: #0f172a; }}
            ::-webkit-scrollbar-thumb {{ background: #334155; border-radius: 4px; }}
            ::-webkit-scrollbar-thumb:hover {{ background: #475569; }}
            body {{ user-select: none; }}
            /* Markdown rendering styles */
            .prose h2 {{ color: #cbd5e1; font-size: 1.1rem; font-weight: bold; margin-top: 1rem; margin-bottom: 0.5rem; }}
            .prose ul {{ list-style-type: disc; padding-left: 1.5rem; margin-bottom: 1rem; color: #94a3b8; }}
            .prose p {{ margin-bottom: 0.75rem; color: #94a3b8; }}
        </style>
    </head>
    <body class="bg-slate-950 text-slate-200 h-screen w-screen flex flex-col font-sans overflow-hidden">

        <!-- Draggable Title Bar (Frameless window support) -->
        <div class="py-3 px-5 bg-slate-900 border-b border-slate-800 flex justify-between items-center" style="-webkit-app-region: drag; cursor: grab;">
            <h1 class="text-sm font-bold text-slate-300 flex items-center gap-2">
                <svg class="w-4 h-4 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path></svg>
                Preflight AI Code Review
            </h1>
            <div class="text-xs text-slate-500">Drag to move</div>
        </div>

        <div class="p-5 flex-grow flex flex-col gap-4 overflow-hidden">

            <!-- Stats Box -->
            <div class="bg-slate-900 border border-slate-800 rounded-xl p-4 relative shadow-lg shrink-0">
                <div class="absolute left-0 top-0 bottom-0 w-1 {indicator_bg} rounded-l-xl"></div>
                <div class="grid grid-cols-2 gap-y-2.5 pl-3">
                    <div class="text-slate-500 text-sm text-right pr-4">Risk Level:</div>
                    <div class="font-mono font-bold {risk_color_class} text-sm">{risk_val} RISK</div>

                    <div class="text-slate-500 text-sm text-right pr-4">AI Confidence:</div>
                    <div class="font-mono font-bold text-white text-sm">{conf_val}%</div>

                    <div class="text-slate-500 text-sm text-right pr-4">Target Branch:</div>
                    <div class="font-mono font-bold text-indigo-400 text-sm">{branch_val}</div>

                    <div class="text-slate-500 text-sm text-right pr-4">Analysis Time:</div>
                    <div class="font-mono text-slate-300 text-sm">{time_val}ms</div>
                </div>
            </div>

            <!-- Expandable Summary Area -->
            <div class="flex-grow flex flex-col min-h-0">
                <button id="toggleBtn" onclick="toggleSummary()" class="w-full py-2.5 mb-3 rounded-lg bg-indigo-500/10 text-indigo-400 font-semibold text-sm border border-indigo-500/20 hover:bg-indigo-500/20 transition-colors flex justify-center items-center gap-2 shrink-0">
                    <span>View Detailed Summary</span>
                    <svg id="toggleIcon" class="w-4 h-4 transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path></svg>
                </button>

                <div id="summaryBox" class="hidden flex-grow bg-[#0b1120] border border-slate-800 rounded-lg p-4 overflow-y-auto shadow-inner prose prose-invert text-sm">
                    {html_summary}
                </div>
            </div>

        </div>

        <!-- Action Buttons (Pinned to Bottom) -->
        <div class="p-4 bg-slate-900 border-t border-slate-800 grid grid-cols-2 gap-4 shrink-0">
            <button onclick="pywebview.api.cancel()" class="py-2.5 rounded-lg bg-slate-800 text-slate-300 font-bold text-sm hover:bg-red-500 hover:text-white transition-colors border border-slate-700 hover:border-red-500">
                Cancel Push
            </button>
            <button onclick="pywebview.api.continuePush()" class="py-2.5 rounded-lg bg-emerald-600 text-white font-bold text-sm hover:bg-emerald-500 transition-colors shadow-lg shadow-emerald-900/20 border border-emerald-500">
                Continue Push
            </button>
        </div>

        <script>
            function toggleSummary() {{
                const box = document.getElementById('summaryBox');
                const btnSpan = document.querySelector('#toggleBtn span');
                const icon = document.getElementById('toggleIcon');

                if (box.classList.contains('hidden')) {{
                    box.classList.remove('hidden');
                    btnSpan.textContent = 'Hide Detailed Summary';
                    icon.classList.add('rotate-180');
                    pywebview.api.resizeWindow(true);
                }} else {{
                    box.classList.add('hidden');
                    btnSpan.textContent = 'View Detailed Summary';
                    icon.classList.remove('rotate-180');
                    pywebview.api.resizeWindow(false);
                }}
            }}
        </script>
    </body>
    </html>
    """

    # 3. Create a temporary API class to handle UI interactions
    class Api:
        def continuePush(self):
            nonlocal decision
            decision = Decision.CONTINUE
            window.destroy()

        def cancel(self):
            nonlocal decision
            decision = Decision.CANCEL
            window.destroy()

        def resizeWindow(self, expand):
            if expand:
                window.resize(520, 700)
            else:
                window.resize(520, 480)

    # 4. Write HTML to a temp file and launch the webview
    fd, temp_path = tempfile.mkstemp(suffix='.html')
    with open(fd, 'w', encoding='utf-8') as f:
        f.write(html_content)

    api = Api()

    # Create window with comfortable default sizing and resizability enabled
    window = webview.create_window(
        'Preflight AI', 
        url=f'file://{temp_path}',
        js_api=api,
        width=520,
        height=480,
        resizable=True,  # Allows users to freely scale the popup window
        frameless=True,  # Removes the default Windows title bar
        easy_drag=False  # Handled by our custom CSS drag region
    )

    # Run the UI (blocks until the window is destroyed)
    webview.start()

    # Cleanup
    try:
        os.remove(temp_path)
    except OSError:
        pass

    return decision