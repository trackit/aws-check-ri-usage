# Check reserved instances usage

This tool will generate a csv report about your usage of reserved instances. Since reserved instances are global to all accounts (if you're organization manages multiple aws accounts, reservation made on account A is accessible on account B), this tool will help to have a quick and easy overview of your infrastructure.



# Usage

```
docker build -it dockerfile/check-ri-usage
docker run -it --rm \
--env AWS_ACCESS_KEY_ID={Your AWS access key} \
--env AWS_SECRET_ACCESS_KEY={Your AWS secret key} \
--env AWS_DEFAULT_REGION={Default region} \
dockerfile/check-ri-usage check-ri-usage.py -o my_report.csv
```
