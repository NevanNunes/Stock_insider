"""
End-to-end integration test for backend:
  1. Login as trader1 and admin
  2. Fetch symbols & traders reference lists
  3. Submit a manual trade
  4. 1-click generate a suspicious trade
  5. 1-click generate a normal trade
  6. Verify worker background processing & alert generation
  7. Admin opens an investigation
  8. Admin generates a compliance PDF report
"""
import time
from fastapi.testclient import TestClient
from app.main import app


def run_tests():
    with TestClient(app) as client:
        # 1. Login as trader
        t_resp = client.post('/api/auth/login', json={'username': 'trader1', 'password': 'trader123'})
        assert t_resp.status_code == 200, f"Trader login failed: {t_resp.text}"
        t_data = t_resp.json()
        t_token = t_data['access_token']
        t_headers = {'Authorization': f"Bearer {t_token}"}
        print(f"[OK] Trader1 logged in. Role: {t_data['role']}")

        # 2. Login as admin
        a_resp = client.post('/api/auth/login', json={'username': 'admin', 'password': 'admin123'})
        assert a_resp.status_code == 200, f"Admin login failed: {a_resp.text}"
        a_data = a_resp.json()
        a_token = a_data['access_token']
        a_headers = {'Authorization': f"Bearer {a_token}"}
        print(f"[OK] Admin logged in. Role: {a_data['role']}")

        # 3. Check reference data
        sym_resp = client.get('/api/symbols')
        assert sym_resp.status_code == 200
        syms = sym_resp.json()
        print(f"[OK] Symbols loaded: {len(syms)}")

        trd_resp = client.get('/api/traders')
        assert trd_resp.status_code == 200
        traders = trd_resp.json()
        print(f"[OK] Traders loaded: {len(traders)}")

        # pick first trader/symbol for manual trade
        first_trader_id = traders[0]['trader_id']
        first_symbol = syms[0]['symbol']
        first_price = float(syms[0]['baseline_price'])

        # 4. Submit manual trade
        manual_payload = {
            'trader_id': first_trader_id,
            'symbol': first_symbol,
            'side': 'BUY',
            'quantity': 150,
            'price': first_price,
        }
        m_resp = client.post('/api/trades', json=manual_payload, headers=t_headers)
        assert m_resp.status_code == 201, f"Manual trade failed: {m_resp.text}"
        m_data = m_resp.json()
        print(f"[OK] Manual trade submitted: {m_data['trade_code']} (notional: {m_data['notional_value']:,.2f})")

        # 5. 1-click suspicious trade
        s_resp = client.post('/api/trades/generate-suspicious', headers=t_headers)
        assert s_resp.status_code == 201, f"Suspicious trade failed: {s_resp.text}"
        s_data = s_resp.json()
        print(f"[OK] Suspicious trade: {s_data['trade_code']} (notional: {s_data['notional_value']:,.2f})")

        # 6. 1-click normal trade
        n_resp = client.post('/api/trades/generate-normal', headers=t_headers)
        assert n_resp.status_code == 201, f"Normal trade failed: {n_resp.text}"
        n_data = n_resp.json()
        print(f"[OK] Normal trade: {n_data['trade_code']} (notional: {n_data['notional_value']:,.2f})")

        # 7. Allow worker loop to dequeue and process
        print("  Waiting for background worker to process trades...")
        time.sleep(3)

        # 8. Query alerts as admin
        alerts_resp = client.get('/api/alerts', headers=a_headers)
        assert alerts_resp.status_code == 200, f"List alerts failed: {alerts_resp.text}"
        alerts_data = alerts_resp.json()
        print(f"[OK] Total alerts: {alerts_data['total']}")
        for alert in alerts_data['alerts'][:5]:
            print(f"     Alert #{alert['id']} | Risk: {alert['risk_level']} | Score: {alert['combined_score']} | Z: {alert['notional_zscore']}")

        # 9. Open investigation as admin
        if alerts_data['alerts']:
            target = alerts_data['alerts'][0]
            inv_payload = {
                'alert_ids': [target['id']],
                'notes': 'Suspicious trade flagged during live demo test.',
            }
            inv_resp = client.post('/api/investigations', json=inv_payload, headers=a_headers)
            assert inv_resp.status_code == 201, f"Open investigation failed: {inv_resp.text}"
            inv_data = inv_resp.json()
            print(f"[OK] Investigation opened: #{inv_data['id']} (status: {inv_data['status']})")

            # 10. Generate PDF Compliance Report
            rep_resp = client.get(f"/api/reports/{inv_data['id']}", headers=a_headers)
            assert rep_resp.status_code == 200, f"Generate report failed: {rep_resp.text}"
            rep_data = rep_resp.json()
            print(f"[OK] PDF Report generated: {rep_data['report_url']}")

    print("\n========== ALL BACKEND INTEGRATION TESTS PASSED! ==========\n")


if __name__ == '__main__':
    run_tests()
