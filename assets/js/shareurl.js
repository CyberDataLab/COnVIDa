if (!window.dash_clientside) {
    window.dash_clientside = {};
}
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

        if (share_button > 0) {
            if (data !== null) {
                delete data['analysis_type']
                // delete data['language']
                delete data['selected_plot_scale']
                delete data['selected_graph_type']
                let u = new URLSearchParams(data).toString();
                output = 'https://convida.inf.um.es/?' + u
                copyToClipboard(output)
                if (data['language'] === 'ES') {
                    alert('URL copiada al portapapeles')
                } else {
                    alert('URL copied to the clipboard')
                }

            }
        }

    }
}