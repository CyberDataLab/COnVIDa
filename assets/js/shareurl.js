if(!window.dash_clientside) {window.dash_clientside = {};}
window.dash_clientside.clientside = {
    display: function (share_button, data) {
        function copyToClipboard(text) {
            var textarea = document.createElement("textarea");
            document.body.appendChild(textarea);
            textarea.value = text;
            textarea.select();
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }

        if (share_button > 0){
            if (data !== null){
                delete data['analysis_type']
                delete data['language']
                delete data['selected_plot_scale']
                delete data['selected_graph_type']
                let u = new URLSearchParams(data).toString();
                output = 'http://localhost:8899/?' + u
                copyToClipboard(output)
                alert('URL copied to the clipboard')
            }
        }

    }
}