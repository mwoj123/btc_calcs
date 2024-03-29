import pandas as pd

import numpy as np
from pycoingecko import CoinGeckoAPI
cg = CoinGeckoAPI()
import streamlit as st
import time


# Streamlit - allows ability to refresh app to see code changes
st.cache(allow_output_mutation=True)

st.title('BTC Will Once Again Rule the Galaxy')
data = {'Date': ['2016-10-08T23:42:17+00:00'
,'2017-10-08T23:42:17+00:00'], 'Transaction Type': ['Buy','Sell'],'Received Quantity':[10,10], 'Received Currency':['BTC','Optional column'], 'Sent Quantity':[290,'Optional column'], 'Sent Currency':['USD','Optional column'],'Fee Currency':['USD','Optional column'], 'Fee Amount':[10,'Optional column'], 'Market Value':[300,'Sent Quantity + fee for buy or - fee for sale'], 'Source':['Coinbase','Optional column']}
sample_sheet = pd.DataFrame(data=data)
sample_sheet.set_index('Date', inplace=True)


# Function to download output as CSV
def convert_df(df):
#IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')

csv = convert_df(sample_sheet)

st.write("Download sample CSV file, if needed, and refresh page")
st.download_button(
    label="Download",
    data=csv,
    file_name='sample.csv',
    mime='text/csv',
)
accounting_method = st.selectbox('Select accounting method', ('', 'FIFO', 'HIFO'))

uploaded_file = st.file_uploader("Choose a file with your historical transactions")
if uploaded_file is not None:
    df = pd.read_csv(
        uploaded_file,
        index_col="Date", 
        infer_datetime_format=True, 
        parse_dates=True
    )
    st.write(df)
balance = st.text_input("Enter your balance before the first transaction that is included in the excel file (ex: 0 if includes all transactions).")
if st.button("Run"):
    with st.spinner('Calculating'):
        time.sleep(3)
    balance = float(balance)


    df_new = df.drop(["Sent Quantity", "Sent Currency", "Fee Currency", "Fee Amount", "Source"], axis=1)
    df_new['Price'] = df_new['Market Value'] / df_new['Received Quantity']
    df_new = df_new.reset_index()
    df_new = df_new.rename(columns={"Date": "Timestamp", "Transaction Type": "Type","Received Quantity":"Amount"})


    df_2 = df_new.drop(["Received Currency", "Market Value"], axis=1)

    df_sell = df_2[df_2['Type'] == 'Sell'].sort_values(by='Timestamp')

    cryptos = cg.get_price(ids='bitcoin', vs_currencies='usd')
    bitcoin_price = cryptos['bitcoin']['usd']

    # Initialize variables to track gains and losses
    gain_loss_df = pd.DataFrame(columns=['Buy Date','Sale Amount','Purchase Price', 'Sell Price', 'Sell Date'])


    if accounting_method == 'FIFO':

        df_buy = df_2[df_2['Type'] == 'Buy'].sort_values(by='Timestamp', ascending=True)
        df_buy['Closed?'] = 'No'
        df_buy['Closed Date'] = 'N/A'
        df_buy['Closed Amount'] = 0
        df_buy['Remaining Amount'] = df_buy['Amount']
        df_buy['Remaining Value'] = df_buy['Remaining Amount'] * bitcoin_price
        df_buy['Unrealized Gains'] = (bitcoin_price - df_buy['Price']) * df_buy['Remaining Amount']


        #FIFO
        # Loop through the trades
        for index, row in df_2.iterrows():
            if row['Type'] == 'Buy':
                balance += row['Amount']
            else:
                if balance >= row['Amount']:
                    balance -= row['Amount']
                    time = row['Timestamp']
                    sell_amount = row['Amount']
                    sell_price = row['Price']
                    
                    for index, row_buy in df_buy.iterrows():
                        
                            
                        if sell_amount - row_buy['Remaining Amount'] >= 0 and row_buy['Closed?'] != 'Yes':

                            sell_amount = sell_amount - row_buy['Remaining Amount']
                            gain_loss_record = pd.Series([row_buy['Timestamp'], row_buy['Remaining Amount'], row_buy['Price'], sell_price, time], index=gain_loss_df.columns)
                            gain_loss_df = gain_loss_df.append(gain_loss_record, ignore_index=True)

                            df_buy.loc[index, 'Closed?'] = 'Yes'
                            df_buy.loc[index, 'Closed Date'] = time
                            df_buy.loc[index, 'Remaining Amount'] = 0
                            df_buy.loc[index, 'Remaining Value'] = 0
                            df_buy.loc[index, 'Unrealized Gains'] = 'Closed'
                            df_buy.loc[index, 'Closed Amount'] = row_buy['Amount']



                        elif sell_amount - row_buy['Remaining Amount'] < 0 and row_buy['Closed?'] != 'Yes':

                            gain_loss_record = pd.Series([row_buy['Timestamp'], sell_amount, row_buy['Price'], sell_price, time], index=gain_loss_df.columns)
                            gain_loss_df = gain_loss_df.append(gain_loss_record, ignore_index=True)

                            df_buy.loc[index, 'Remaining Amount'] = row_buy['Remaining Amount'] - sell_amount
                            df_buy.loc[index, 'Closed?'] = 'Partial'
                            df_buy.loc[index, 'Closed Date'] = 'Partial'
                            df_buy.loc[index, 'Remaining Value'] = (row_buy['Remaining Amount'] - sell_amount) * bitcoin_price
                            df_buy.loc[index, 'Unrealized Gains'] = (bitcoin_price - row_buy['Price']) * (row_buy['Remaining Amount'] - sell_amount)
                            df_buy.loc[index, 'Closed Amount'] = row_buy['Amount'] - (row_buy['Remaining Amount'] - sell_amount)
                            break

                        else:
                            continue

                    else:
                        continue 
                    
                        
                else:
                    
                    print("Error, NOT GONNA MAKE IT. More has been sold than is in current balance.")



    else:

        df_buy = df_2[df_2['Type'] == 'Buy'].sort_values(by='Price', ascending=False)
        df_buy['Closed?'] = 'No'
        df_buy['Closed Date'] = 'N/A'
        df_buy['Closed Amount'] = 0
        df_buy['Remaining Amount'] = df_buy['Amount']
        df_buy['Remaining Value'] = df_buy['Remaining Amount'] * bitcoin_price
        df_buy['Unrealized Gains'] = (bitcoin_price - df_buy['Price']) * df_buy['Remaining Amount']


        # Loop through the trades HIFO
        for index, row in df_2.iterrows():
            if row['Type'] == 'Buy':
                balance += row['Amount']
            else:
                if balance >= row['Amount']:
                    balance -= row['Amount']
                    time = row['Timestamp']
                    sell_amount = row['Amount']
                    sell_price = row['Price']
                    
                    for index, row_buy in df_buy.iterrows():
                        if row_buy['Timestamp'] < time:
                            
                            if sell_amount - row_buy['Remaining Amount'] >= 0 and row_buy['Closed?'] != 'Yes':
                                
                                sell_amount = sell_amount - row_buy['Remaining Amount']
                                gain_loss_record = pd.Series([row_buy['Timestamp'], row_buy['Remaining Amount'], row_buy['Price'], sell_price, time], index=gain_loss_df.columns)
                                gain_loss_df = gain_loss_df.append(gain_loss_record, ignore_index=True)
                                
                                df_buy.loc[index, 'Closed?'] = 'Yes'
                                df_buy.loc[index, 'Closed Date'] = time
                                df_buy.loc[index, 'Remaining Amount'] = 0
                                df_buy.loc[index, 'Remaining Value'] = 0
                                df_buy.loc[index, 'Unrealized Gains'] = 'Closed'
                                df_buy.loc[index, 'Closed Amount'] = row_buy['Amount']



                            elif sell_amount - row_buy['Remaining Amount'] < 0 and row_buy['Closed?'] != 'Yes':
                                
                                gain_loss_record = pd.Series([row_buy['Timestamp'], sell_amount, row_buy['Price'], sell_price, time], index=gain_loss_df.columns)
                                gain_loss_df = gain_loss_df.append(gain_loss_record, ignore_index=True)
                                
                                df_buy.loc[index, 'Remaining Amount'] = row_buy['Remaining Amount'] - sell_amount
                                df_buy.loc[index, 'Closed?'] = 'Partial'
                                df_buy.loc[index, 'Closed Date'] = 'Partial'
                                df_buy.loc[index, 'Remaining Value'] = (row_buy['Remaining Amount'] - sell_amount) * bitcoin_price
                                df_buy.loc[index, 'Unrealized Gains'] = (bitcoin_price - row_buy['Price']) * (row_buy['Remaining Amount'] - sell_amount)
                                df_buy.loc[index, 'Closed Amount'] = row_buy['Amount'] - (row_buy['Remaining Amount'] - sell_amount)
                                break
                                
                            else:
                                continue

                        else:
                            continue 
                    
                        
                else:
                    
                    print("Error, NOT GONNA MAKE IT. More has been sold than is in current balance.")

                    st.text('Your bitcoin balance is:')



    st.text('Your bitcoin balance is:')
    balance



    df_buy = df_buy.sort_values(by='Timestamp')

    st.text('')
    st.text('')
    st.text('')
    st.text('Here are your realized gains/losses')

    gain_loss_df['Gain/Loss'] = (gain_loss_df['Sell Price'] - gain_loss_df['Purchase Price']) * gain_loss_df['Sale Amount']
    #gain_loss_df

    st.write(gain_loss_df)

    st.text('')
    st.text('')
    st.text('Form 8949 format:')

    # Prior to dropping the 'Sale Amount' and 'Sell Price' columns
    gain_loss_df['Proceeds'] = gain_loss_df['Sale Amount'] * gain_loss_df['Sell Price']

    # Create the result dataframe
    result_df = gain_loss_df.copy()

    # Append "BTC" to the Sale Amount column
    result_df['Sale Amount BTC'] = result_df['Sale Amount'].astype(str) + " BTC"

    # Create Cost Basis column as Purchase Price times the Sale Amount
    result_df['Cost Basis'] = result_df['Purchase Price'] * result_df['Sale Amount']

    # Drop the columns you don't want
    result_df = result_df.drop(columns=['Sale Amount', 'Purchase Price', 'Sell Price', 'Gain/Loss'])

    # Reorder the columns
    result_df = result_df[['Sale Amount BTC', 'Buy Date', 'Cost Basis', 'Sell Date', 'Proceeds']]

    # Convert 'Buy Date' and 'Sell Date' to string and slice the first 10 characters
    result_df['Buy Date'] = result_df['Buy Date'].astype(str).str[:10]
    result_df['Sell Date'] = result_df['Sell Date'].astype(str).str[:10]

    # Rename the columns
    result_df = result_df.rename(columns={
        'Sale Amount BTC': 'Currency Name',
        'Buy Date': 'Purchase Date',
        'Cost Basis': 'Cost Basis',
        'Sell Date': 'Date Sold',
        'Proceeds': 'Proceeds'
    })

    st.write(result_df)

    st.text('')
    st.text('Here are the gains/losses for each purchase tax lot')

    gain_loss_by_buy_day = gain_loss_df[['Buy Date','Sale Amount', 'Gain/Loss']]
    gain_loss_by_buy_day = gain_loss_by_buy_day.groupby(['Buy Date']).sum()
    gain_loss_by_buy_day

    st.text('')
    st.text('')
    st.text('')
    st.text('Here are the gains/losses for each sell transaction')

    gain_loss_by_sell_day = gain_loss_df[['Sell Date','Sale Amount', 'Gain/Loss']]
    gain_loss_by_sell_day = gain_loss_by_sell_day.groupby(['Sell Date']).sum()
    gain_loss_by_sell_day

    # Function to download output as CSV

    def convert_df(df):
    #IMPORTANT: Cache the conversion to prevent computation on every rerun
        return df.to_csv().encode('utf-8')

    csv_output = convert_df(df_buy)

    st.write("Click to download results as a CSV")
    st.download_button(
        label="Download",
        data=csv_output,
        file_name='output.csv',
        mime='text/csv',
    )

    tax_output = convert_df(result_df)

    st.write("Click to download 8949")
    st.download_button(
        label="Download 8949 first 5 columns",
        data=tax_output,
        file_name='tax_output.csv',
        mime='text/csv',
    )
