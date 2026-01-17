import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify
from werkzeug.utils import secure_filename
from app.services.csv_parser import CSVParser
from app.services.transaction_service import TransactionService

bp = Blueprint("upload", __name__, url_prefix="/upload")


def allowed_file(filename):
    """許可されたファイル形式かチェック"""
    return "." in filename and filename.rsplit(".", 1)[1].lower() == "csv"


@bp.route("/", methods=["GET"])
def upload_form():
    """CSVアップロードフォーム表示"""
    return render_template("upload.html")


@bp.route("/process", methods=["POST"])
def process_upload():
    """CSVファイルをアップロードして処理"""

    # ファイルチェック
    if "file" not in request.files:
        return jsonify({"error": "ファイルが選択されていません"}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "ファイルが選択されていません"}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "CSVファイルのみアップロード可能です"}), 400

    try:
        # ファイル保存
        filename = secure_filename(file.filename)
        from flask import current_app

        upload_folder = current_app.config["UPLOAD_FOLDER"]
        filepath = os.path.join(upload_folder, filename)
        file.save(filepath)

        # CSV解析
        transactions, parse_errors = CSVParser.parse_csv(filepath)

        # 解析エラーをフォーマット
        formatted_parse_errors = []
        for error in parse_errors:
            formatted_parse_errors.append(
                {
                    "row": error.get("row", "-"),
                    "error": error.get("error", "不明なエラー"),
                    "data": error.get("data", {}),
                    "type": "parse_error",
                }
            )

        if not transactions and parse_errors:
            return (
                jsonify(
                    {
                        "error": "CSVの解析に失敗しました",
                        "result": {
                            "total": len(parse_errors),
                            "success": 0,
                            "failed": len(parse_errors),
                            "parse_errors": len(parse_errors),
                            "all_errors": formatted_parse_errors,
                        },
                    }
                ),
                400,
            )

        # データベースに保存
        result = TransactionService.save_transactions(transactions)

        # 保存エラーをフォーマット
        formatted_save_errors = []
        for error in result["errors"]:
            formatted_save_errors.append(
                {
                    "row": "-",
                    "error": error.get("error", "不明なエラー"),
                    "data": error.get("data", {}),
                    "type": "save_error",
                }
            )

        # 全てのエラーを結合
        all_errors = formatted_parse_errors + formatted_save_errors

        # 一時ファイル削除（オプション）
        # os.remove(filepath)

        return jsonify(
            {
                "success": True,
                "message": f"処理が完了しました",
                "result": {
                    "total": len(transactions) + len(parse_errors),
                    "success": result["success"],
                    "failed": result["failed"] + len(parse_errors),
                    "parse_errors": len(parse_errors),
                    "save_errors": result["failed"],
                    "all_errors": all_errors,  # 全てのエラーを返す
                },
            }
        )

    except Exception as e:
        return jsonify({"error": f"予期しないエラーが発生しました: {str(e)}"}), 500
