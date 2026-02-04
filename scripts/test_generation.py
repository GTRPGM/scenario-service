# scripts/test_generation.py

import asyncio
import sys

import httpx

SCENARIO_SERVICE_URL = "http://localhost:8030"  # 시나리오 서비스 주소


async def test_scenario_generation(concept: str):
    print(f"[*] 시나리오 생성 요청 중... 컨셉: {concept}")

    url = f"{SCENARIO_SERVICE_URL}/api/v1/generation/pure"
    payload = {"concept": concept}

    async with httpx.AsyncClient(
        timeout=300.0
    ) as client:  # LLM 생성이므로 타임아웃 넉넉히
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()

            print("\n[+] 시나리오 생성 완료!")
            print("=" * 50)
            print(f"줄거리 요약: {result['data']['summary']}")
            print("=" * 50)

            print("\n[액트(Acts) 구성]")
            for act in result["data"]["acts"]:
                print(f"- {act['name']} ({act['id']}): {act['goal']}")

            print("\n[세부 시퀀스(Sequences)]")
            for seq in result["data"]["sequences"]:
                print(f"\n[{seq['name']} @ {seq['location_name']}]")
                print(f"묘사: {seq['description']}")
                print(f"목표: {seq['goal']}")
                print(f"트리거: {', '.join(seq['exit_triggers'])}")

        except httpx.HTTPStatusError as e:
            print(f"[!] 에러 발생: {e.response.status_code}")
            print(f"상세 내용: {e.response.text}")
        except Exception as e:
            print(f"[!] 네트워크 에러: {str(e)}")


if __name__ == "__main__":
    test_concept = (
        "기계 문명이 멸망하고 마법이 다시 깨어난 포스트 아포칼립스 세계관에서의 첫 모험"
    )
    if len(sys.argv) > 1:
        test_concept = sys.argv[1]

    asyncio.run(test_scenario_generation(test_concept))
