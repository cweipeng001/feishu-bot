"""
飞书机器人与Qoder集成测试脚本
用于测试各个功能模块
"""

import requests
import json
import sys


def test_health_check(base_url="http://localhost:5000"):
    """测试健康检查接口"""
    print("=" * 50)
    print("测试健康检查接口...")
    print("=" * 50)
    
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 健康检查通过")
            return True
        else:
            print("❌ 健康检查失败")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False


def test_send_message(base_url="http://localhost:5000", chat_id=None):
    """测试发送消息接口"""
    print("\n" + "=" * 50)
    print("测试发送消息接口...")
    print("=" * 50)
    
    if not chat_id:
        chat_id = input("请输入飞书群组或用户的chat_id: ")
    
    message = input("请输入要发送的测试消息（默认: 测试消息）: ") or "测试消息"
    
    try:
        response = requests.post(
            f"{base_url}/test/send",
            json={"chat_id": chat_id, "message": message},
            timeout=10
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            print("✅ 消息发送成功")
            return True
        else:
            print("❌ 消息发送失败")
            return False
    except Exception as e:
        print(f"❌ 发送消息异常: {e}")
        return False


def test_feishu_callback(base_url="http://localhost:5000"):
    """模拟测试飞书回调"""
    print("\n" + "=" * 50)
    print("模拟测试飞书回调...")
    print("=" * 50)
    
    # 模拟URL验证请求
    url_verification_data = {
        "type": "url_verification",
        "challenge": "test_challenge_123456",
        "token": "test_token"
    }
    
    try:
        print("\n1. 测试URL验证...")
        response = requests.post(
            f"{base_url}/feishu/callback",
            json=url_verification_data,
            timeout=10
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200 and response.json().get("challenge") == "test_challenge_123456":
            print("✅ URL验证测试通过")
        else:
            print("❌ URL验证测试失败")
            
    except Exception as e:
        print(f"❌ 回调测试异常: {e}")
        return False
    
    return True


def test_qoder_integration():
    """测试Qoder集成（需要Qoder服务运行）"""
    print("\n" + "=" * 50)
    print("测试Qoder智能体集成...")
    print("=" * 50)
    
    qoder_endpoint = input("请输入Qoder API端点（默认: http://localhost:8080/api/chat）: ") or "http://localhost:8080/api/chat"
    api_key = input("请输入Qoder API Key（可选）: ") or ""
    
    headers = {
        "Content-Type": "application/json"
    }
    
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    data = {
        "message": "你好，这是一条测试消息",
        "user_id": "test_user",
        "chat_id": "test_chat",
        "context": {
            "platform": "feishu",
            "source": "feishu_bot"
        }
    }
    
    try:
        response = requests.post(
            qoder_endpoint,
            headers=headers,
            json=data,
            timeout=30
        )
        print(f"状态码: {response.status_code}")
        print(f"响应: {response.json()}")
        
        if response.status_code == 200:
            print("✅ Qoder集成测试通过")
            return True
        else:
            print("❌ Qoder集成测试失败")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到Qoder服务，请确保Qoder服务正在运行")
        return False
    except Exception as e:
        print(f"❌ Qoder集成测试异常: {e}")
        return False


def main():
    """主测试函数"""
    print("\n")
    print("╔" + "=" * 48 + "╗")
    print("║" + " " * 10 + "飞书机器人与Qoder集成测试" + " " * 10 + "║")
    print("╚" + "=" * 48 + "╝")
    print("\n")
    
    base_url = input("请输入服务地址（默认: http://localhost:5000）: ") or "http://localhost:5000"
    
    # 执行测试
    results = {
        "健康检查": test_health_check(base_url),
        "飞书回调": test_feishu_callback(base_url),
    }
    
    # 询问是否测试发送消息
    if input("\n是否测试发送消息到飞书？(y/n，默认: n): ").lower() == "y":
        results["发送消息"] = test_send_message(base_url)
    
    # 询问是否测试Qoder集成
    if input("\n是否测试Qoder智能体集成？(y/n，默认: n): ").lower() == "y":
        results["Qoder集成"] = test_qoder_integration()
    
    # 输出测试结果汇总
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    for test_name, result in results.items():
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    total = len(results)
    passed = sum(results.values())
    print(f"\n总计: {passed}/{total} 项测试通过")
    
    if passed == total:
        print("\n🎉 所有测试通过！")
        return 0
    else:
        print(f"\n⚠️  有 {total - passed} 项测试失败，请检查配置和服务状态")
        return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n测试已取消")
        sys.exit(1)
