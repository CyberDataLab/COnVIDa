if(!window.dash_clientside) {window.dash_clientside = {};}
window.dash_clientside.clientside = {
    display: function (share_button, data) {
        function copyToClipboard(text) {
            var dummy = document.createElement("textarea");
            document.body.appendChild(dummy);
            dummy.value = text;
            dummy.select();
            document.execCommand("copy");
            document.body.removeChild(dummy);
            // alert('URL copied!')
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