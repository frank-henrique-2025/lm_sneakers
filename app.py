from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import pymysql
import requests
import re

app = Flask(__name__)
CORS(app)

def get_connection():
    return pymysql.connect(
        host="shinkansen.proxy.rlwy.net",
        user="root",
        password="wplSYcrJOPkWQrdpfBGgVSuJsOHDbDzk",
        database="railway",
        port=53516,
        cursorclass=pymysql.cursors.DictCursor
    )

@app.route('/register', methods=['POST'])
def register():
    try:
        json_data = request.json
        codigo_rastreio = json_data.get('codigoRastreio')
        status = json_data.get('statusPedido')
        numero_pedido = json_data.get('numeroPedido')
        data_entrega = json_data.get('dataEntrega')
        nome_cliente = json_data.get('nomeCliente')
        telefone_cliente = json_data.get('telefoneCliente')

        # Define data_status como data atual (DD/MM/YYYY)
        data_status = datetime.now().strftime("%Y-%m-%d")

        conexao = get_connection()
        with conexao.cursor() as cursor:
            # Verifica se o código de rastreio já existe
            query_check = """SELECT codigo_rastreio FROM rastreios WHERE codigo_rastreio = %s"""
            cursor.execute(query_check, (codigo_rastreio,))
            resultado = cursor.fetchone()

            if resultado:
                return jsonify({"mensagem": "Pedido já registrado!"})

            # Insere no banco incluindo a coluna data_status
            query_insert = """
                INSERT INTO rastreios (
                    codigo_rastreio,
                    status_pedido,
                    numero_pedido,
                    data_envio,
                    data_entrega,
                    nome_cliente,
                    telefone_cliente,
                    data_status
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            valores = (
                codigo_rastreio,
                status,
                numero_pedido,
                data_status,
                data_entrega,
                nome_cliente,
                telefone_cliente,
                data_status
            )
            cursor.execute(query_insert, valores)
            conexao.commit()

        return jsonify({"mensagem": "Pedido registrado!", "codigo_rastreio": codigo_rastreio})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao registrar pedido!", "erro": f"Error: '{e}'"})

@app.route('/get_pedido', methods=['POST'])
def get_pedido():
    def formatData(data):
        try:
            data_formatada = datetime.strptime(data, "%Y-%m-%d")
            data_final = data_formatada.strftime("%d %B %Y")

            meses = {
                "January": "Janeiro", "February": "Fevereiro", "March": "Março",
                "April": "Abril", "May": "Maio", "June": "Junho",
                "July": "Julho", "August": "Agosto", "September": "Setembro",
                "October": "Outubro", "November": "Novembro", "December": "Dezembro"
            }

            for en, pt in meses.items():
                data_final = data_final.replace(en, pt)

            return str(data_final)

        except Exception as e:
            return f"Error: '{e}'"

    try:
        codigo_rastreio = request.json.get('codigoRastreio')

        conexao = get_connection()
        with conexao.cursor() as cursor:
            # Seleciona também a coluna telefone_cliente e data_status
            query = """
                SELECT
                    codigo_rastreio,
                    status_pedido,
                    numero_pedido,
                    data_envio,
                    data_entrega,
                    nome_cliente,
                    telefone_cliente,
                    data_status
                FROM rastreios
                WHERE codigo_rastreio = %s
            """
            cursor.execute(query, (codigo_rastreio,))
            resultado = cursor.fetchone()

        if resultado:
            data_entrega = str(resultado["data_entrega"]) if resultado["data_entrega"] else ""
            data_envio = str(resultado["data_envio"]) if resultado["data_envio"] else ""
            data_status = str(resultado["data_status"]) if resultado["data_status"] else ""

            data_entrega_formatada = ""
            if data_entrega:
                data_entrega_formatada = formatData(data_entrega)
                if 'Error' in data_entrega_formatada:
                    return jsonify({"mensagem": "Erro ao buscar pedido!", "erro": data_entrega_formatada})

            data_envio_formatada = ""
            if data_envio:
                data_envio_formatada = formatData(data_envio)
                if 'Error' in data_envio_formatada:
                    return jsonify({"mensagem": "Erro ao buscar pedido!", "erro": data_envio_formatada})

            data_status_formatada = ""
            if data_status:
                data_status_formatada = formatData(data_envio)
                if 'Error' in data_status_formatada:
                    return jsonify({"mensagem": "Erro ao buscar pedido!", "erro": data_status_formatada})

            return jsonify({
                "codigo_rastreio": resultado["codigo_rastreio"],
                "status_pedido": resultado["status_pedido"],
                "numero_pedido": resultado["numero_pedido"],
                "data_entrega": data_entrega_formatada,
                "nome_cliente": resultado["nome_cliente"],
                "data_envio": data_envio_formatada,
                "telefone_cliente": resultado["telefone_cliente"],
                "data_status": resultado["data_status"]
            })
        else:
            return jsonify({"mensagem": "Nenhum pedido localizado!"})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao buscar pedido!", "erro": f"Error: '{e}'"})

@app.route('/newStatus', methods=['POST'])
def newStatus():
    try:
        new_status = request.json.get('newStatus')

        conexao = get_connection()
        with conexao.cursor() as cursor:
            query_check = "SELECT COUNT(*) FROM situacao WHERE status_pedido = %s"
            cursor.execute(query_check, (new_status,))
            resultado = cursor.fetchone()

            if resultado['COUNT(*)'] > 0:
                return jsonify({"mensagem": "Status já registrado!"})
            else:
                query_insert = "INSERT INTO situacao (status_pedido) VALUES (%s)"
                cursor.execute(query_insert, (new_status,))
                conexao.commit()

        return jsonify({"mensagem": "Status registrado!"})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao registrar status!", "erro": f"Error: '{e}'"})

@app.route('/getStatus', methods=['GET'])
def getStatus():
    try:
        conexao = get_connection()
        with conexao.cursor() as cursor:
            query_select = "SELECT status_pedido FROM situacao"
            cursor.execute(query_select)
            status_list = [status['status_pedido'] for status in cursor.fetchall()]

        return jsonify({"status_list": status_list})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao buscar status!", "erro": f"Error: '{e}'"})

@app.route('/deleteStatus', methods=['POST'])
def deleteStatus():
    try:
        statusToDelete = request.json.get('statusToDelete')

        conexao = get_connection()
        with conexao.cursor() as cursor:
            query_delete = "DELETE FROM situacao WHERE status_pedido = %s"
            cursor.execute(query_delete, (statusToDelete,))
            conexao.commit()

        return jsonify({"mensagem": "Status removido!"})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao remover status!", "erro": f"Error: '{e}'"})

@app.route('/editRegistro', methods=['POST'])
def editRegistro():
    try:
        codigo_rastreio = request.json.get('codigoRastreio')
        status_pedido = request.json.get('statusPedido')
        numero_pedido = request.json.get('numeroPedido')
        data_entrega = request.json.get('dataEntrega')
        nome_cliente = request.json.get('nomeCliente')
        data_envio = request.json.get('dataEnvio')
        telefone_cliente = request.json.get('telefoneCliente')

        conexao = get_connection()
        with conexao.cursor() as cursor:
            # Além de status_pedido, buscamos também data_status
            query_atual = """
                SELECT status_pedido, data_status
                FROM rastreios
                WHERE codigo_rastreio = %s
            """
            cursor.execute(query_atual, (codigo_rastreio,))
            row = cursor.fetchone()

            if not row:
                return jsonify({"mensagem": "Erro ao editar registro!", 'erro': "Código de rastreio não encontrado!"})

            atual_status = row['status_pedido']
            atual_data_status = row['data_status'] if row['data_status'] else ""

            # Se o status foi alterado, atualizamos a data_status para a data atual
            novo_data_status = atual_data_status
            if atual_status != status_pedido:
                enviar_sms(telefone_cliente, atual_status, status_pedido)
                novo_data_status = datetime.now().strftime("%Y-%m-%d")

            query_update = """
                UPDATE rastreios
                SET status_pedido = %s,
                    numero_pedido = %s,
                    data_entrega = %s,
                    nome_cliente = %s,
                    data_envio = %s,
                    telefone_cliente = %s,
                    data_status = %s
                WHERE codigo_rastreio = %s
            """
            valores = (
                status_pedido,
                numero_pedido,
                data_entrega,
                nome_cliente,
                data_envio,
                telefone_cliente,
                novo_data_status,
                codigo_rastreio
            )
            cursor.execute(query_update, valores)
            conexao.commit()

        return jsonify({"mensagem": "Registro editado!"})

    except Exception as e:
        return jsonify({"mensagem": "Erro ao editar registro!", 'erro': f"Error: '{e}'"})

def enviar_sms(telefone_cliente, atual_status, status_pedido):
    telefone_cliente = re.sub(r'\D', '', telefone_cliente)

    usuario_ = "0QS5fuI6z2x2MdJoTHxRae3WGpcNIkaGCOqIDItgMJAlYw37OI1kDAqv4+Cwg6/FR1P5Qo0BUJQ8Yxln4Qr9Vw=="
    senha_   = "yrWI7PtPtrQQvBsWBkmg7JcpmSgpxUrB+/6c+ftKsrczDZ9H8Ci3MYm9oq2Riftv8mzxeuCX+yC52MA0x2yzGA=="

    url_token = "https://api.assertivasolucoes.com.br/oauth2/v3/token"
    head_token = {
        'content-type': "application/x-www-form-urlencoded",
        'grant_type': "client_credentials"
    }
    response_token = requests.post(url_token, auth=HTTPBasicAuth(usuario_, senha_), data=head_token, verify=False)
    access_token = response_token.json().get('access_token', '')

    url_sms = "https://api.assertivasolucoes.com.br/sms/v3/send"
    head_sms = {
        "Content-Type": "application/json",
        'Authorization': f'Bearer {access_token}'
    }
    payload_sms = {
        "can_receive_status": False,
        "can_receive_answer": False,
        "webhook_status_url": "",
        "webhook_answer_url": "",
        "route_type": 1,
        "arraySms": [{
            "number": telefone_cliente,
            "message": f"LM SNEAKERS informa: O status do seu pedido foi atualizado de {atual_status} para {status_pedido}. Acesse o link e confira agora mesmo: (https://lmsneakers.netlify.app/)",
            "filter_value": ""
        }]
    }
    response_sms = requests.post(url_sms, headers=head_sms, json=payload_sms)
    if "id_sms" in response_sms.text:
        return True
    else:
        return False

if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=5000)